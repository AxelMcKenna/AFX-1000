#pragma once
#include "rmx/FactoryEchoReturn.h"
#include "IsolateNeutral.h"
namespace rmx::research {
using Block=std::array<rmx::Stereo,32>;
using Biquad=rmx::research::IsolateNeutral::Biquad;
struct SpiralMotionPitch {
    std::array<rmx::Stereo,4096> ring{};unsigned writer{},reader{},second{},windowBlocks{},change{};
    float fraction{},window{},fade{},direct{1};bool down{};Biquad filter;
    explicit SpiralMotionPitch(bool direction):reader(4096-(direction?640:1792)),change(direction?48:117),down(direction){
        filter.c={.7878031134605408f,0,-.7878031134605408f,-.42026737332344055f,-.5756062865257263f};
    }
    unsigned wrap(int value)const noexcept{return static_cast<unsigned>(value+8192)%4096;}
    void restart(bool direction){
        writer=second=windowBlocks=0;reader=4096-(direction?640:1792);
        change=direction?48:117;fraction=window=fade=0;direct=1;down=direction;filter.state={};
    }
    Block read(unsigned& cursor,float& phase,float increment){
        Block result{};
        for(unsigned i=0;i<32;++i){
            if(down){result[i]=ring[wrap(static_cast<int>(cursor)-1)]*phase+ring[cursor]*(1-phase);phase+=increment;if(phase<1)cursor=(cursor+1)%4096;else phase-=1;}
            else{result[i]=ring[cursor]*(1-phase)+ring[(cursor+1)%4096]*phase;phase+=increment;cursor=(cursor+1)%4096;while(phase>=1){phase-=1;cursor=(cursor+1)%4096;}}
        }
        return result;
    }
    void process(const Block& input,Block& output,unsigned raw){
        for(auto x:input){ring[writer]=x;writer=(writer+1)%4096;}
        float increment=down?raw*.003921568859368563f:raw<=129?raw*.007692307699471712f:(raw-130)*.01600000075995922f+1;
        if(change>=9)increment=0;
        const float initial=fraction;auto primary=read(reader,fraction,increment);
        const auto distance=(writer+4096-reader)%4096;
        if(windowBlocks||(down?distance*2>2176:distance*2<3072)){
            if(!windowBlocks)second=wrap(static_cast<int>(reader)+(down?512:-1792));
            float phase=initial;const auto alternate=read(second,phase,increment);
            for(unsigned i=0;i<32;++i){const float complement=1-window,shape=window*complement+.5f,a=(complement*shape)*2,b=(window*shape)*2;primary[i]=primary[i]*a+alternate[i]*b;window+=down?.0022321429569274187f:.002604166977107525f;}
            if(++windowBlocks>=(down?14u:12u)){reader=second;windowBlocks=0;window=0;}
        }
        filter.process(primary,output);
        if(change){
            const float delta=change>5?0.f:.00625f;if(change>5){fade=0;direct=1;}
            for(unsigned i=0;i<32;++i){fade+=delta;direct-=delta;output[i]=input[i]*direct+output[i]*fade;}
            --change;
        }
    }
};

// Four separately weighted input streams retain their own returning tails.
struct SpiralMovingReturn {
    std::array<std::vector<Stereo>,4> lines;
    std::array<float,4> weights{},targets{},steps{},readGain{};unsigned writer{},age{},blocks{},lastTime{};
    float sendGate{1};bool enabled{true};
    float activation{},activationTarget{-1},activationStep{};unsigned activationBlocks{};
    SpiralMovingReturn(){for(auto& line:lines)line.resize(24004);}
    void restart(){
        weights=targets=steps=readGain={};writer=age=blocks=lastTime=activationBlocks=0;
        sendGate=1;enabled=true;activation=activationStep=0;activationTarget=-1;
    }
    void controls(unsigned time,unsigned main,bool active){
        enabled=active;
        if(time!=lastTime){
            lastTime=time;targets={};const float position=std::clamp((static_cast<int>(time)-3)/62.25f,0.f,4.f);const auto upper=std::min(3u,static_cast<unsigned>(position));
            if(upper>0)targets[upper-1]=upper+1-position;targets[upper]=position-upper;if(position==4)targets[3]=1;
            for(unsigned i=0;i<4;++i)steps[i]=(targets[i]-weights[i])*.00625f;blocks=5;
        }
        const float target=main<4?0.f:main<=8?main*.2f-.8f:1.f;
        if(target!=activationTarget){activationTarget=target;activationStep=(target-activation)*.00625f;activationBlocks=5;}
    }
    Stereo process(Stereo input){
        Stereo sum{};activation+=activationStep;sendGate=std::clamp(sendGate+(enabled?.00625f:-.00625f),0.f,1.f);
        for(unsigned i=0;i<4;++i){
            weights[i]+=steps[i];const unsigned delay=(i+1)*6000;readGain[i]=std::clamp(readGain[i]+((age/32*32)>=delay?.00625f:-.00625f),0.f,1.f);const auto tap=age>=delay?lines[i][(writer+24004-delay)%24004]*readGain[i]:Stereo{};
            sum=sum+tap;const auto feed=(((input*weights[i])*activation)*sendGate)*.7079457640647888f;lines[i][writer]=feed+tap*.75f;
        }
        writer=(writer+1)%24004;++age;return sum*.7f;
    }
    void endBlock(){
        if(blocks&&!--blocks){weights=targets;steps={};}
        if(activationBlocks&&!--activationBlocks){activation=activationTarget;activationStep=0;}
    }
};

// Research Default48k/120BPM processor. Qualification belongs to the recorded
// reference campaigns; live delivery and selection lifecycle are separate checks.
struct SpiralMotion {
    struct Controls {unsigned main{128},time{},pitch{};bool enabled{true};int direction{-1};} controls;
    int lastDesired{-2},pendingRestart{-1};unsigned historyWritten{};
    bool down{},first{true},descending{},active{true},initialized{},dryRestart{true},dryWarming{true};unsigned currentMain{128},writer{},quiet{},activityCount{},dryBlocks{},rawWriter{},rawAge{},primaryAge{},privateAge{};
    float rawMix{1},rawStep{},primaryGain{},privateGain{},commonWet{},commonStep{.00625f};bool rawArmed{};
    float dryTarget{1},dryStep{},activityAverage{},inputGate{1},inputGain{1},dryGain{1},outputGain{},average{},held{},phase{},velocity{},acceleration{},targetVelocity{};
    double delay{};
    Biquad inputFilter,high,low,post;SpiralMotionPitch pitch;
    std::vector<Stereo> history,rawHistory;SpiralMovingReturn echoes;
    explicit SpiralMotion(bool direction):down(direction),pitch(direction),history(196608),rawHistory(32768){
        inputFilter.c={.29287490248680115f,.5857498049736023f,.29287490248680115f,-7.176304665877298e-17f,.1714995801448822f};
        high.c={.9682207107543945f,-1.936441421508789f,.9682207107543945f,-1.9362547397613525f,.9366280436515808f};
        low.c={.29549500346183777f,.5909900069236755f,.29549500346183777f,.015271740034222603f,.1667083203792572f};
        post.c={.1419954150915146f,.2839908301830292f,.1419954150915146f,-.19833816587924957f,-.23368017375469208f};
        delay=targetDelay(128);outputGain=targetGain(down?1.2f:1.5f);
    }
    unsigned targetDelay(unsigned raw)const{
        const float p=raw<=3?0.f:(raw-3)*.003968254197388887f;
        const auto ms=down?(raw<=3?10u:static_cast<unsigned>(p*490.f+10.f)):(raw<=3?100u:static_cast<unsigned>(((255-raw)*.003968254197388887f)*95.f+5.f));
        return ms*48;
    }
    float targetGain(float loopGain)const{
        return std::min(1-((1-std::min(static_cast<float>(delay)*1.0416666555101983e-5f,1.f))*.1809999942779541f+.3199999928474426f)*loopGain,.30000001192092896f)*1.4125374555587769f;
    }
    void restartPrivate(bool direction){
        down=direction;initialized=descending=false;active=true;dryRestart=dryWarming=true;
        writer=quiet=activityCount=dryBlocks=rawAge=primaryAge=privateAge=historyWritten=0;
        rawMix=1;rawStep=primaryGain=privateGain=activityAverage=average=held=phase=velocity=acceleration=targetVelocity=0;
        rawArmed=false;inputGate=inputGain=1;inputFilter.state=high.state=low.state=post.state={};
        pitch.restart(direction);echoes.restart();lastDesired=-2;
    }
    void updateDelay(unsigned target){
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
    void process(std::span<const Stereo,32> input,std::span<Stereo,32> output){
        for(auto x:input){rawHistory[rawWriter]=x;rawWriter=(rawWriter+1)%32768;}
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
            const int ago=integer-static_cast<int>(i);const auto a=ago>0&&static_cast<unsigned>(ago)<=historyWritten?history[(writer+i+196608-integer)%196608]:Stereo{},b=ago>=0&&static_cast<unsigned>(ago+1)<=historyWritten?history[(writer+i+196608-integer-1)%196608]:Stereo{};primaryGain=std::min(1.f,primaryGain+(primaryReady?.00625f:0.f));const auto tap=(a*(1-fraction))*primaryGain+(b*fraction)*primaryGain;
            rawMix+=rawStep;rawInputGain+=inputStep;
            const auto old=rawHistory[(rawWriter+i+32768-target)%32768];const auto direct=(old*rawMix)*rawInputGain;const auto loop=tap*(1-rawMix);
            wet[i]={std::clamp((direct.l+wet[i].l)+loop.l,-held,held),std::clamp((direct.r+wet[i].r)+loop.r,-held,held)};
        }
        if(rawMix<std::abs(rawStep)){rawMix=rawStep=0;}
        high.process(wet,wet);low.process(wet,wet);for(unsigned i=0;i<32;++i)history[(writer+i)%196608]=wet[i]*loopGain;writer=(writer+32)%196608;historyWritten=std::min(historyWritten+32,196608u);
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
        for(unsigned i=0;i<32;++i){dryGain+=dryStep;const auto y=delayed[i];const auto tail=echoes.process(y);if(privateAge++<160)privateGain+=.00625f;commonWet+=commonStep;output[i]=input[i]*dryGain+((y+tail)*privateGain)*commonWet;}
        if(privateGain>1-.00625f)privateGain=1;
        if(commonWet>1-.00625f){commonWet=1;commonStep=0;}
        if(commonWet<.00625f){commonWet=commonStep=0;if(desired>=0&&desired!=static_cast<int>(down))pendingRestart=desired;}
        if(privateAge==32)dryRestart=true;
        if(dryBlocks&&!--dryBlocks){dryGain=dryTarget;dryStep=0;dryWarming=false;}
        echoes.endBlock();if(active!=controls.enabled)dryRestart=true;active=controls.enabled;
    }
};
}
