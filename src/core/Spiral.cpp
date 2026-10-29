#include "rmx/CalibratedSpiral.h"
#include <functional>

namespace rmx {
bool CalibratedSpiral::prepare(std::span<Stereo> storage,std::span<Stereo> rawStorage) noexcept {
    bool invalid=storage.size()<storageFrames||rawStorage.size()<rawStorageFrames;
    if(!invalid){const std::less<const Stereo*> less;invalid=less(storage.data(),rawStorage.data()+rawStorageFrames)&&less(rawStorage.data(),storage.data()+storageFrames);}
    if(invalid){history=rawHistory={};pitch.ring={};echoes.lines={};prepared=storageActive=rawActive=false;rawWriter=rawWritten=0;return false;}
    history=storage.first(32768);pitch.ring=storage.subspan(32768,4096);
    for(unsigned i=0;i<4;++i)echoes.lines[i]=storage.subspan(32768+4096+i*24004,24004);
    rawHistory=rawStorage.first(rawStorageFrames);prepared=true;reset();return true;
}
void CalibratedSpiral::configure() noexcept {
        inputFilter.c={.29287490248680115f,.5857498049736023f,.29287490248680115f,-7.176304665877298e-17f,.1714995801448822f};
        high.c={.9682207107543945f,-1.936441421508789f,.9682207107543945f,-1.9362547397613525f,.9366280436515808f};
        low.c={.29549500346183777f,.5909900069236755f,.29549500346183777f,.015271740034222603f,.1667083203792572f};
        post.c={.1419954150915146f,.2839908301830292f,.1419954150915146f,-.19833816587924957f,-.23368017375469208f};
    pitch.filter.c={.7878031134605408f,0,-.7878031134605408f,-.42026737332344055f,-.5756062865257263f};
}
void CalibratedSpiral::resetState(bool preserveRaw) noexcept {
    const auto h=history,r=rawHistory,p=pitch.ring;const auto e=echoes.lines;const auto target=controls;
    const auto write=rawWriter,written=rawWritten;const bool ready=prepared,active=storageActive,raw=rawActive;
    *this=CalibratedSpiral{};history=h;rawHistory=r;pitch.ring=p;echoes.lines=e;controls=target;
    prepared=ready;storageActive=active;rawActive=raw;if(preserveRaw){rawWriter=write;rawWritten=written;}configure();
}
void CalibratedSpiral::reset() noexcept {resetState(false);storageActive=rawActive=false;}
void CalibratedSpiral::setStorageState(bool active,bool rawAvailable) noexcept {
    rawAvailable=rawAvailable&&prepared;active=active&&rawAvailable;
    if(rawAvailable!=rawActive)rawWriter=rawWritten=0;
    if(active!=storageActive)resetState(true);
    storageActive=active;rawActive=rawAvailable;
}
void CalibratedSpiral::setControls(Controls target) noexcept {
    target.main=std::min(target.main,255u);target.time=std::min(target.time,255u);target.pitch=std::min(target.pitch,255u);
    target.direction=std::clamp(target.direction,-1,1);controls=target;
}
void CalibratedSpiral::recordRaw(std::span<const Stereo,32> input) noexcept {
    if(!prepared||!rawActive)return;
    for(auto x:input){rawHistory[rawWriter]=x;rawWriter=(rawWriter+1)%32768;}
    rawWritten=std::min(rawWritten+32,32768u);
}
unsigned CalibratedSpiral::targetDelay(unsigned raw) const noexcept {
        const float p=raw<=3?0.f:(raw-3)*.003968254197388887f;
        const auto ms=down?(raw<=3?10u:static_cast<unsigned>(p*490.f+10.f)):(raw<=3?100u:static_cast<unsigned>(((255-raw)*.003968254197388887f)*95.f+5.f));
        return ms*48;
    }
float CalibratedSpiral::targetGain(float loopGain) const noexcept {
        return std::min(1-((1-std::min(static_cast<float>(delay)*1.0416666555101983e-5f,1.f))*.1809999942779541f+.3199999928474426f)*loopGain,.30000001192092896f)*1.4125374555587769f;
    }
void CalibratedSpiral::restartPrivate(bool direction) noexcept {
        down=direction;initialized=descending=false;active=true;dryRestart=dryWarming=true;
        writer=quiet=activityCount=dryBlocks=rawAge=primaryAge=privateAge=historyWritten=0;
        rawMix=1;rawStep=primaryGain=privateGain=activityAverage=average=held=phase=velocity=acceleration=targetVelocity=0;
        rawArmed=false;inputGate=inputGain=1;inputFilter.state=high.state=low.state=post.state={};
        pitch.restart(direction);echoes.restart();lastDesired=-2;
    }
void CalibratedSpiral::updateDelay(unsigned target) noexcept {
        const int difference=static_cast<int>(target)-static_cast<int>(delay);constexpr int limit=24000;
        if(difference>0){
            const int amount=std::max(difference,limit);const float z=1-(1.f/static_cast<float>(limit))*static_cast<float>(amount);
            targetVelocity=(1-(z*z)*z)*(down?.17001047730445862f:.10000000149011612f)+.009999999776482582f;
            acceleration=(targetVelocity-velocity)*.02083333395421505f;
        }else if(difference<0){
            const int amount=std::max(difference,-limit);
            if(velocity<-.009999999776482582f&&amount>=-47){
                targetVelocity=-.009999999776482582f;
                acceleration=(-1.f/static_cast<float>(std::min(amount,-32)))*(targetVelocity-velocity);
            }else{
                const float z=(1.f/static_cast<float>(limit))*static_cast<float>(amount)+1;
                targetVelocity=(((z*z)*z)-1)*(down?.17001047730445862f:.7019171118736267f)-.009999999776482582f;
                acceleration=(targetVelocity-velocity)*.02083333395421505f;
            }
        }
        if(difference==0&&velocity>-.010999999940395355f&&velocity<.010999999940395355f){delay=target;velocity=acceleration=targetVelocity=0;}
    }
void CalibratedSpiral::process(std::span<const Stereo,32> input,std::span<Stereo,32> output) noexcept {
        if(!prepared||!storageActive){std::copy(input.begin(),input.end(),output.begin());return;}
        if(first&&!controls.enabled){std::copy(input.begin(),input.end(),output.begin());return;}
        if(first){first=false;if(controls.direction>=0){down=controls.direction!=0;pitch.restart(down);}lastDesired=static_cast<int>(down);for(unsigned i=0;i<32;++i)commonWet+=commonStep;commonStep=(1-commonWet)*.00625f;std::copy(input.begin(),input.end(),output.begin());return;}
        if(pendingRestart>=0){restartPrivate(pendingRestart!=0);pendingRestart=-1;}
        if(!initialized){initialized=true;currentMain=controls.main;delay=targetDelay(currentMain);const float x=currentMain<=3?0.f:(currentMain-3)*.003968254197388887f;inputGain=std::min(4*x,1.f);outputGain=targetGain(.8f+std::min(10*x,1.f)*(down?.4f:.7f));}
        if(currentMain<controls.main)++currentMain;else if(currentMain>controls.main)--currentMain;
        const float position=currentMain<=3?0.f:(currentMain-3)*.003968254197388887f;
        const float nextInput=std::min(4*position,1.f),inputStep=(nextInput-inputGain)*.03125f,previousInputGain=inputGain;
        if(dryRestart){dryRestart=false;dryWarming=true;dryBlocks=0;}
        if(!dryBlocks){dryTarget=active&&down&&position>.5f?2-2*position:1;dryStep=(dryTarget-dryGain)*(dryWarming?.00625f:.03125f);dryBlocks=dryWarming?5:1;}
        const float loopGain=std::min(10*position,1.f)*(active?(down?.4f:.7f):.19300000369548798f)+.8f;
        if(controls.enabled&&!active)held=std::min(activityAverage*1.5f,1.f);
        float peak=0;Block wet{},delayed{};
        for(unsigned i=0;i<32;++i){peak=std::max(peak,std::abs((input[i].l+input[i].r)*.5f));inputGain+=inputStep;inputGate=std::clamp(inputGate+(active?.00625f:-.00625f),0.f,1.f);wet[i]=(input[i]*inputGate)*inputGain;}
        if(inputGain<std::abs(inputStep))inputGain=0;if(inputGain>1-std::abs(inputStep))inputGain=1;
        const float weighted=average*186.f+peak;average=static_cast<float>(static_cast<double>(weighted)/187.);held=std::max(held,average);
        inputFilter.process(wet,wet);const int previousInteger=static_cast<int>(delay);updateDelay(targetDelay(controls.main));
        std::array<int,32> integers{};std::array<float,32> fractions{};
        for(unsigned i=0;i<32;++i){
            velocity=std::clamp(velocity+acceleration,-2.f,.8f);delay+=static_cast<double>(velocity);
            int integer=static_cast<int>(delay);float fraction=static_cast<float>(delay-integer);
            if(descending){phase-=2.0833333564951317e-6f;if(phase< -1){descending=false;phase=-2-phase;}}
            else{phase+=2.0833333564951317e-6f;if(phase>1){descending=true;phase=2-phase;}}
            const int whole=static_cast<int>(phase);integer+=whole;fraction+=phase-whole;if(phase<0){--integer;fraction+=1;}
            integers[i]=integer;fractions[i]=fraction;
        }
        const auto target=targetDelay(controls.main);bool primaryReady=true;
        if(primaryAge<target*8){primaryReady=primaryAge>=static_cast<unsigned>(delay)+484;primaryAge+=32;}
        if(!rawArmed){rawAge+=32;if(rawAge>=target+484){rawArmed=true;rawStep=-.00625f;}}
        float rawInputGain=previousInputGain;
        // The reference cache is anchored before the delay update. Its per-sample
        // integer offsets are relative to the first new index, not the old index.
        for(unsigned i=0;i<32;++i){
            const int integer=previousInteger+integers[i]-integers[0];const float fraction=fractions[i];
            const int ago=integer-static_cast<int>(i);const auto a=ago>0&&static_cast<unsigned>(ago)<=historyWritten?history[(writer+i+32768-integer)%32768]:Stereo{},b=ago>=0&&static_cast<unsigned>(ago+1)<=historyWritten?history[(writer+i+32768-integer-1)%32768]:Stereo{};primaryGain=std::min(1.f,primaryGain+(primaryReady?.00625f:0.f));const auto tap=(a*(1-fraction))*primaryGain+(b*fraction)*primaryGain;
            rawMix+=rawStep;rawInputGain+=inputStep;
            const unsigned rawAgo=target-i;const auto old=rawAgo<=rawWritten?rawHistory[(rawWriter+i+32768-target)%32768]:Stereo{};const auto direct=(old*rawMix)*rawInputGain;const auto loop=tap*(1-rawMix);
            wet[i]={std::clamp((direct.l+wet[i].l)+loop.l,-held,held),std::clamp((direct.r+wet[i].r)+loop.r,-held,held)};
        }
        if(rawMix<std::abs(rawStep)){rawMix=rawStep=0;}
        high.process(wet,wet);low.process(wet,wet);for(unsigned i=0;i<32;++i)history[(writer+i)%32768]=wet[i]*loopGain;writer=(writer+32)%32768;historyWritten=std::min(historyWritten+32,32768u);
        // This output regulator is deliberately slow: one update per sample at 1/96000.
        const float gainStep=(targetGain(loopGain)-outputGain)*1.0416666555101983e-5f;post.process(wet,wet);
        float activityPeak=0;
        for(unsigned i=0;i<32;++i){outputGain+=gainStep;wet[i]=(wet[i]*1.2999999523162842f)*outputGain;++quiet;const float activity=std::abs((wet[i].l+wet[i].r)*.5f);activityPeak=std::max(activityPeak,activity);if(activity>=held*.001f)quiet=0;}
        if(quiet>=4801){held*=.8912509083747864f;quiet=0;}
        if(activityCount<=1498){const float sum=activityAverage*static_cast<float>(activityCount)+activityPeak;++activityCount;activityAverage=static_cast<float>(static_cast<double>(sum)/activityCount);}
        else{activityAverage=(activityAverage*1499.f+activityPeak)*.0006666666595265269f;activityCount=1500;}
        pitch.process(wet,delayed,controls.pitch);echoes.controls(controls.time,controls.main,active);
        const int desired=controls.enabled?(controls.direction<0?static_cast<int>(down):controls.direction):-1;
        if(desired!=lastDesired){commonStep=((desired<0||desired==static_cast<int>(down)?1.f:0.f)-commonWet)*.00625f;lastDesired=desired;dryRestart=true;}
        for(unsigned i=0;i<32;++i){dryGain+=dryStep;const auto y=delayed[i];const auto tail=echoes.process(y);if(privateAge<160){++privateAge;privateGain+=.00625f;}commonWet+=commonStep;output[i]=input[i]*dryGain+((y+tail)*privateGain)*commonWet;}
        if(privateGain>1-.00625f)privateGain=1;
        if(commonWet>1-.00625f){commonWet=1;commonStep=0;}
        if(commonWet<.00625f){commonWet=commonStep=0;if(desired>=0&&desired!=static_cast<int>(down))pendingRestart=desired;}
        if(privateAge==32)dryRestart=true;
        if(dryBlocks&&!--dryBlocks){dryGain=dryTarget;dryStep=0;dryWarming=false;}
        echoes.endBlock();if(active!=controls.enabled)dryRestart=true;active=controls.enabled;
    }
}
