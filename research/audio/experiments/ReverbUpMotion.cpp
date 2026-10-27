#include "ReverbUpMotion.h"
#include "ReverbUpControlCalibration.h"
#include <stdexcept>

namespace rmx {
namespace {
float roomScale(int raw) noexcept {
    const float v=1.f-static_cast<float>(std::max(0,raw-3))*(1.f/252.f);
    return .3f+3.f*((v*v)*(v*v));
}
constexpr std::array<std::array<int,2>,5> roomBases{{{1032,1146},{1060,1856},{1145,1961},{1916,1115},{1992,1190}}};
double mainMix(int raw) noexcept {return std::min(1.,4.*std::max(0,raw-3)/252);}
float dryLevel(int) noexcept {return 1.f;}
double returnShape(int main,int amount) noexcept {
    const double a=amount<=127?1:.65+.35*std::pow((255.-amount)/128,2);
    return .7*(a+std::pow(std::min(1.,main/183.),2)*std::pow(1-a,3));
}
double inputShape(int main) noexcept {
    const int audible=std::max(4,main);const auto& row=reverbUpControls[static_cast<size_t>(audible)];
    const double numerator=(1-row.inputA[1])/2;
    return row.wetGain/(mainMix(audible)*returnShape(audible,128)*numerator);
}
double decay(int raw) noexcept {return 1+49*std::pow(std::max(0.,raw-3.)/252,3);}
}
void ReverbUpMotion::Delay::prepare(size_t maximum){data.assign(maximum+1,0);head=0;}
void ReverbUpMotion::Delay::clear() noexcept {std::fill(data.begin(),data.end(),0);head=0;}
double ReverbUpMotion::Delay::tap(size_t delay) const noexcept {return data[(head+data.size()-delay)%data.size()];}
void ReverbUpMotion::Delay::push(double value) noexcept {data[head]=value;if(++head==data.size())head=0;}
void ReverbUpMotion::Filter::biquad(double hz,bool high) noexcept {
    const double w=2*std::numbers::pi*hz/48000,alpha=std::sin(w)/std::sqrt(2.);
    b0=(1+(high?1:-1)*std::cos(w))/2/(1+alpha);b1=(high?-2:2)*b0;b2=b0;
    a1=-2*std::cos(w)/(1+alpha);a2=(1-alpha)/(1+alpha);
}
void ReverbUpMotion::Filter::onePole(double hz,bool high) noexcept {
    const double t=std::tan(std::numbers::pi*hz/48000),pole=(1-t)/(1+t);
    b0=high?(1+pole)/2:(1-pole)/2;b1=high?-b0:b0;b2=0;a1=-pole;a2=0;
}
void ReverbUpMotion::Filter::clear() noexcept {s1=s2=0;}
double ReverbUpMotion::Filter::tick(double x) noexcept {const double y=b0*x+s1;s1=b1*x-a1*y+s2;s2=b2*x-a2*y;return y;}
void ReverbUpMotion::AllPass::prepare(size_t size){length=size;delay.prepare(size);}
double ReverbUpMotion::AllPass::tick(double x) noexcept {const double y=delay.tap(length)-.7*x;delay.push(x+.7*y);return y;}

void ReverbUpMotion::prepare(size_t maxFrames){
    if(!maxFrames||maxFrames>maximumCallbackFrames)throw std::invalid_argument("Reverb callback capacity must be 1..4096");
    for(size_t j=0;j<5;++j)for(size_t ch=0;ch<2;++ch){
        size_t maximum=1;
        for(const auto& row:reverbUpControls)maximum=std::max(maximum,static_cast<size_t>(row.delays[j][ch]));
        maximum=std::max(maximum,static_cast<size_t>(std::ceil(3.3*roomBases[j][ch]))+2);
        combs[j][ch].prepare(maximum);
    }
    for(auto& chain:inputFilters){chain[1].b0=1;}
    for(auto& filter:outputHigh)filter.biquad(17330,false);
    for(auto& pair:feedbackFilters)for(auto& filter:pair){filter.b0=reverbUpFeedback[0];filter.b1=reverbUpFeedback[1];filter.a1=reverbUpFeedback[2];}
    allpasses[0][0].prepare(335);allpasses[0][1].prepare(1091);
    allpasses[1][0].prepare(395);allpasses[1][1].prepare(1031);
    callbackInput.assign(maxFrames,{});reset();
}
void ReverbUpMotion::reset() noexcept {
    for(auto& pair:combs)for(auto& delay:pair)delay.clear();
    for(auto& chain:allpasses)for(auto& ap:chain)ap.delay.clear();
    for(auto& chain:inputFilters)for(auto& filter:chain)filter.clear();
    for(auto& filter:outputFilter)filter.clear();for(auto& filter:outputHigh)filter.clear();
    for(auto& pair:feedbackFilters)for(auto& filter:pair)filter.clear();
    collected={};pending={};pendingDry={};received=available=outputHead=0;
    delays={};delayCurrent={};delayTarget={};delayStep={};coefficients={};targetCoefficients={};steps={};stagedRemaining={};
    started=prepared=activationPrepared=lastSelected=everActivated=geometryStart=amountStart=false;
    slowMain=pendingMain=0;mainPeriod=60;sharedBlocks=geometryRemaining=mixRemaining=0;frame=32;inputAge=0;
    fastMix=fastMixTarget=fastMixStep=0;dryGain=compensation=1;startupFade=inputFade=dryStep=0;dryCurrent=dryTarget=1;
    warmRemaining=dryRemaining=dryRestart=0;state={};
}
void ReverbUpMotion::setControls(Controls controls) noexcept {
    controls.main=std::clamp(controls.main,0,255);controls.amount=std::clamp(controls.amount,0,255);
    controls.cutoff=std::clamp(controls.cutoff,0,255);target=controls;
}
void ReverbUpMotion::initialize() noexcept {configure(target);started=true;}
ReverbUpMotion::Input ReverbUpMotion::ingest(Stereo input) noexcept {
    float routing=1;if(inputAge<160){startupFade+=.00625f;routing=startupFade;}
    const Stereo routed{static_cast<float>(static_cast<float>(input.l*routing)*routing),
                        static_cast<float>(static_cast<float>(input.r*routing)*routing)};
    inputFade=std::clamp(inputFade+(state.enabled?.00625f:-.00625f),0.f,1.f);
    std::array<double,2> source{routed.l,routed.r};for(auto& value:source)value*=inputFade;
    const bool selected=inputAge>=32&&state.enabled;++inputAge;
    return {routed,source,selected};
}
void ReverbUpMotion::control(bool selected) noexcept {
    const auto approach=[](int a,int b){return a+(a<b?1:(a>b?-1:0));};
    Controls c=state;c.main=approach(c.main,target.main);c.cutoff=approach(c.cutoff,target.cutoff);c.enabled=target.enabled;
    if(!everActivated&&selected){
        c=target;slowMain=pendingMain=c.main;mainPeriod=60;
        sharedBlocks=geometryRemaining=mixRemaining=0;stagedRemaining.fill(0);steps.fill(0);prepared=false;
    }
    geometryStart=amountStart=false;
    if(!sharedBlocks){
        if(slowMain!=target.main){
            const int desired=15-std::min(5,std::abs(target.main-slowMain));mainPeriod=approach(mainPeriod,desired);
            pendingMain=approach(slowMain,target.main);sharedBlocks=static_cast<size_t>(mainPeriod);geometryStart=true;
        }else if(c.amount!=target.amount){c.amount=approach(c.amount,target.amount);sharedBlocks=5;amountStart=true;}
    }
    configure(c);
}
void ReverbUpMotion::configure(Controls c) noexcept {
    if(!prepared){slowMain=pendingMain=c.main;fastMix=mainMix(c.main);}
    const int roomMain=geometryStart?pendingMain:slowMain;
    const auto& row=reverbUpControls[static_cast<size_t>(roomMain)];
    if(!prepared||geometryStart){
        const float scale=roomScale(roomMain);
        for(size_t j=0;j<5;++j)for(size_t ch=0;ch<2;++ch){
            float requested=scale*static_cast<float>(roomBases[j][ch]);
            if(roomMain>=4){const auto measured=row.delays[j][ch];if(static_cast<int>(requested)!=measured)requested=static_cast<float>(measured);}
            delayTarget[j][ch]=requested;
            if(!prepared)delayCurrent[j][ch]=requested;
            delayStep[j][ch]=sharedBlocks?(requested-delayCurrent[j][ch])*(1.f/static_cast<float>(sharedBlocks*32)):0;
            delays[j][ch]=static_cast<int>(delayCurrent[j][ch]);
        }
        geometryRemaining=sharedBlocks*32;
    }
    const double effectiveDecay=geometryStart&&c.main<=3?std::min(8.,decay(c.amount)):decay(c.amount);
    const double exponent=decay(128)/effectiveDecay;
    std::array<double,15> requested{};
    for(size_t j=0;j<5;++j){
        const auto& feedbackRow=roomMain<4?reverbUpControls[4]:row;
        const double hiddenScale=roomMain<4?roomScale(roomMain)/roomScale(4):1;
        requested[j]=std::pow(feedbackRow.gainL[j],exponent*hiddenScale);
        requested[j+5]=std::pow(feedbackRow.gainR[j],exponent*hiddenScale);
    }
    double wet=row.wetGain*reverbUpAmountGain[static_cast<size_t>(c.amount)]/reverbUpAmountGain[128];
    wet*=1+reverbUpMainCorrection[static_cast<size_t>(roomMain)]*reverbUpAmountCorrection[static_cast<size_t>(c.amount)];
    const int audibleMain=std::max(4,slowMain),targetAudible=std::max(4,roomMain);
    const auto& filterRow=reverbUpControls[static_cast<size_t>(std::max(4,c.main))];
    const double numerator=(1-filterRow.inputA[1])/2;
    requested[10]=inputShape(std::max(4,c.main));
    const double targetSend=inputShape(targetAudible);
    const double roomNumerator=(1-reverbUpControls[static_cast<size_t>(targetAudible)].inputA[1])/2;
    requested[11]=roomMain<4?returnShape(roomMain,c.amount):wet/(targetSend*mainMix(roomMain)*roomNumerator);
    requested[12]=filterRow.inputA[0];requested[13]=filterRow.inputA[1];requested[14]=numerator;
    if(c.main!=state.main){fastMixTarget=mainMix(c.main);fastMixStep=(fastMixTarget-fastMix)/32;mixRemaining=32;}
    if(!prepared){coefficients=targetCoefficients=requested;prepared=true;}
    else for(size_t j=0;j<15;++j)if(requested[j]!=targetCoefficients[j]){
        if(j>=12){coefficients[j]=targetCoefficients[j]=requested[j];stagedRemaining[j]=0;continue;}
        if(j!=10&&!geometryStart&&!amountStart)continue;
        const size_t length=j==10?1:(geometryStart?(j<10?sharedBlocks*32:160):
            (j<10?160:static_cast<size_t>(c.amount<state.amount?2000:1500)*32));
        targetCoefficients[j]=requested[j];stagedRemaining[j]=length;
        steps[j]=(requested[j]-coefficients[j])/static_cast<double>(length);
    }
    compensation=1+.5*c.cutoff/255;dryGain=dryLevel(c.main);
    if(!activationPrepared){inputFade=c.enabled?1.f:0.f;dryCurrent=dryTarget=1;activationPrepared=true;}
    else if(c.main!=state.main&&lastSelected)setDry(static_cast<float>(dryGain),32);
    const double hz=54*std::pow(6310./54,std::max(0.,static_cast<double>(c.cutoff)-4)/251);
    for(auto& filter:outputFilter)filter.biquad(hz,true);state=c;
}
void ReverbUpMotion::setDry(float next,size_t length) noexcept {
    dryTarget=next;dryRemaining=length;dryStep=(next-dryCurrent)*(1.f/static_cast<float>(length));
}
std::array<Stereo,2> ReverbUpMotion::tick(Input input) noexcept {
    if(geometryRemaining)for(size_t j=0;j<5;++j)for(size_t ch=0;ch<2;++ch)delays[j][ch]=static_cast<int>(delayCurrent[j][ch]);
    if(mixRemaining){fastMix+=fastMixStep;if(!--mixRemaining)fastMix=fastMixTarget;}
    if(frame%32==31&&sharedBlocks&&!--sharedBlocks)slowMain=pendingMain;
    for(size_t j=0;j<15;++j)if(stagedRemaining[j]){
        if(j>=10||!warmRemaining)coefficients[j]+=steps[j];
        if(!--stagedRemaining[j])coefficients[j]=targetCoefficients[j];
    }
    ++frame;
    if(input.selected!=lastSelected){
        lastSelected=input.selected;setDry(static_cast<float>(input.selected?dryGain:1),160);
        if(input.selected&&!everActivated){everActivated=true;warmRemaining=12416;dryRestart=frame+32;}
    }
    if(dryRestart&&frame==dryRestart){setDry(dryTarget,160);dryRestart=0;}
    if(dryRemaining){dryCurrent+=dryStep;--dryRemaining;}
    const bool warming=warmRemaining;
    auto source=input.source;std::array<double,2> wet{};
    for(size_t ch=0;ch<2;++ch){
        auto& bandpass=inputFilters[ch][0];bandpass.b0=coefficients[14];bandpass.b1=0;bandpass.b2=-coefficients[14];
        bandpass.a1=coefficients[12];bandpass.a2=coefficients[13];
        source[ch]*=coefficients[10]*fastMix;
        for(auto& filter:inputFilters[ch])source[ch]=filter.tick(source[ch]);
    }
    for(size_t j=0;j<5;++j){
        const double left=warming?0:combs[j][0].tap(static_cast<size_t>(delays[j][0]))*coefficients[j];
        const double right=warming?0:combs[j][1].tap(static_cast<size_t>(delays[j][1]))*coefficients[j+5];
        const double fl=feedbackFilters[j][0].tick(left),fr=feedbackFilters[j][1].tick(right);
        combs[j][0].push(source[0]+fr);combs[j][1].push(warming&&j==0?0:source[1]+fl);
        wet[0]+=left;wet[1]+=right;
    }
    if(geometryRemaining){
        for(size_t j=0;j<5;++j)for(size_t ch=0;ch<2;++ch){
            if(!warming)delayCurrent[j][ch]+=delayStep[j][ch];
            if(geometryRemaining==1)delayCurrent[j][ch]=delayTarget[j][ch];delays[j][ch]=static_cast<int>(delayCurrent[j][ch]);
        }
        --geometryRemaining;
    }
    for(size_t ch=0;ch<2;++ch){
        for(auto& ap:allpasses[ch])wet[ch]=ap.tick(wet[ch]);
        wet[ch]=outputHigh[ch].tick(outputFilter[ch].tick(wet[ch]))*coefficients[11];
    }
    if(warming)--warmRemaining;
    const double direct=dryCurrent;
    const Stereo dry{static_cast<float>(input.routed.l*direct),static_cast<float>(input.routed.r*direct)};
    const Stereo output{static_cast<float>(input.routed.l*direct+compensation*wet[0]),static_cast<float>(input.routed.r*direct+compensation*wet[1])};
    if(!dryRemaining){dryCurrent=dryTarget;dryStep=0;}
    return {output,dry};
}
bool ReverbUpMotion::process(std::span<const Stereo> input,std::span<Stereo> output,std::span<Stereo> dry) noexcept {
    if(input.size()!=output.size()||(!dry.empty()&&(dry.size()!=input.size()||dry.data()==output.data()))||input.size()>callbackInput.size())return false;
    if(input.empty())return true;
    if(callbackInput.empty())return false;
    for(const auto sample:input)if(!std::isfinite(sample.l)||!std::isfinite(sample.r))return false;
    if(!started)initialize();
    std::copy(input.begin(),input.end(),callbackInput.begin());
    std::copy_n(callbackInput.begin(),input.size(),output.begin());
    if(!dry.empty())std::copy_n(callbackInput.begin(),input.size(),dry.begin());
    size_t read=0,written=0;
    while(read<input.size()){
        const auto take=std::min(32-received,input.size()-read);
        for(size_t i=0;i<take;++i)collected[received+i]=ingest(callbackInput[read+i]);
        received+=take;read+=take;
        const auto emit=std::min(available,input.size()-written);
        for(size_t i=0;i<emit;++i){output[written+i]=pending[outputHead+i];if(!dry.empty())dry[written+i]=pendingDry[outputHead+i];}
        written+=emit;available-=emit;outputHead+=emit;
        if(received==32){
            control(collected[0].selected);
            for(size_t i=0;i<32;++i){const auto result=tick(collected[i]);pending[i]=result[0];pendingDry[i]=result[1];}
            received=0;available=32;outputHead=0;
        }
    }
    return true;
}
size_t ReverbUpMotion::storageBytes() const noexcept {
    size_t bytes=callbackInput.capacity()*sizeof(Stereo);
    for(const auto& pair:combs)for(const auto& delay:pair)bytes+=delay.data.capacity()*sizeof(double);
    for(const auto& chain:allpasses)for(const auto& ap:chain)bytes+=ap.delay.data.capacity()*sizeof(double);
    return bytes;
}
}
