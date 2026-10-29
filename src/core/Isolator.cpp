#include "rmx/Isolator.h"
#include <numbers>

namespace rmx {
namespace {
float db(float value) { return std::pow(10.f,value/20); }
double wrap(double value) { return value-std::floor(value); }
float gain(float control,int minimum,int maximum) {
    constexpr float maxima[]{0,3,6,9},minima[]{6,12,18,0};
    // Public reference controls quantize to 8-bit travel. Factory measurements
    // show unity at raw 124..131, with linear amplitude on either side.
    const auto raw=std::clamp(static_cast<int>(std::floor((control+1)*127.5f+1.e-4f)),0,255);
    if(raw<124) {
        const float travel=std::clamp((124-raw)/123.f,0.f,1.f);
        const float endpoint=minimum==3?0.f:db(-minima[std::clamp(minimum,0,3)]);
        return 1+travel*(endpoint-1);
    }
    const float travel=std::clamp((raw-131)/123.f,0.f,1.f);
    return 1+travel*(db(maxima[std::clamp(maximum,0,3)])-1);
}
constexpr std::array<std::array<double,4>,3> addTimes{{{{.125,.25,.5,1}},{{.125,.375,.625,.875}},{{.25,.5,.75,1}}}};
constexpr std::array<std::array<double,5>,3> rollTimes{{{{1,.5,.25,.125,.0625}},{{1,.75,.5,.25,.125}},{{.5,.25,.125,.0625,.03125}}}};
constexpr float strengths[]{.5f,1.f,1.5f};
}
void Isolator::prepare(double sampleRate) {
    rate=sampleRate;
    // The longest pattern is one beat at 40 BPM (1.5 seconds), with margin.
    for(auto& band:bands) {band.history.prepare(static_cast<size_t>(rate*2)+4);band.capture.assign(static_cast<size_t>(rate*2)+4,{});}
    attack=1-std::exp(-1.f/static_cast<float>(rate*.001));release=1-std::exp(-1.f/static_cast<float>(rate*.025));
    gateAttack=attack;gateRelease=1-std::exp(-1.f/static_cast<float>(rate*.015));
    transSlew=1-std::exp(-1.f/static_cast<float>(rate*.0005));
    kickSlowAlpha=1-std::exp(-1.f/static_cast<float>(rate*.25));kickDecay=std::exp(-1.f/static_cast<float>(rate*.09));
    kickFilter.configure(180,.7071f,rate);configured=false;configure(settings);reset();
}
std::array<std::span<Stereo>,6> Isolator::loanableStorage() noexcept {
    std::array<std::span<Stereo>,6> storage{};
    for(size_t i=0;i<3;++i){storage[i*2]=bands[i].history.loanableStorage();storage[i*2+1]=bands[i].capture;}
    return storage;
}
void Isolator::setStorageLoaned(bool loaned) noexcept {
    if(storageLoaned==loaned)return;
    storageLoaned=loaned;
    // Returning a loan invalidates history in constant time. Captures become
    // readable only after their ordinary recording path has filled them again.
    for(auto& band:bands){band.history.invalidate();band.captured=band.length=0;band.position=0;band.recording=false;}
}
void Isolator::reset() noexcept {
    storageLoaned=false;
    lowState={};highState={};kickFilter.reset();cutHighPass.reset();cutLowPass.reset();
    for(auto& filter:lowCrossover)filter.reset();
    for(auto& filter:highCrossover)filter.reset();
    kickFast=kickSlow=kickGate=0;kickRefractory=0;frame=0;lastMid=lastHigh=2;
    for(auto& band:bands) {band.history.reset();band.captured=band.length=0;band.position=0;band.recording=false;band.envelope=0;band.gate=band.transGain=1;}
}
void Isolator::configure(const IsolatorSettings& next) noexcept {
    if(configured&&next==settings) return;
    configured=true;settings=next;
    lowAlpha=poleCoefficient(std::clamp(settings.lowHz,40.f,1000.f),rate);
    highAlpha=poleCoefficient(std::clamp(settings.highHz,settings.lowHz+100,static_cast<float>(rate*.45)),rate);
    for(auto& filter:lowCrossover)filter.configure(settings.lowHz,std::numbers::sqrt2_v<float>*.5f,rate);
    for(auto& filter:highCrossover)filter.configure(settings.highHz,std::numbers::sqrt2_v<float>*.5f,rate);
    lastMid=lastHigh=2;
}
Stereo Isolator::cut(Stereo input,const std::array<float,3>& controls) noexcept {
    const auto bass=kickFilter.process(input).low;
    const float magnitude=peak(bass);
    kickFast+=(magnitude-kickFast)*(magnitude>kickFast?attack:release);
    kickSlow+=(kickFast-kickSlow)*kickSlowAlpha;
    if(kickRefractory) --kickRefractory;
    if(kickRefractory==0&&kickFast>std::max(.008f,kickSlow*1.8f)) {kickGate=1;kickRefractory=static_cast<unsigned>(rate*.12);}
    else kickGate*=kickDecay;
    const auto kick=bass*kickGate, residual=input-kick;
    const float mid=std::max(0.f,-controls[1]),hi=std::max(0.f,-controls[2]);
    if((frame&31u)==0||lastMid==2||lastHigh==2) {
        cutHighPass.configure(25*std::pow(600.f,mid),settings.cutHpfResonance?2.f:.7071f,rate);
        cutLowPass.configure(18000*std::pow(1.f/900,hi),settings.cutLpfResonance?2.f:.7071f,rate);
        lastMid=mid;lastHigh=hi;
    }
    // Both filters run even at neutral so switching a knob does not expose
    // stale state. Only the non-kick residual is fed to these manual filters.
    const auto high= cutHighPass.process(residual).high;
    const auto afterHigh=mix(residual,high,mid);
    const auto low=cutLowPass.process(afterHigh).low;
    const float reduction=std::min(1.f,std::max(0.f,-controls[0])*strengths[std::clamp(settings.kickStrength,0,2)]);
    return kick*(1-reduction)+mix(afterHigh,low,hi);
}
Stereo Isolator::roll(Band& band,Stereo input,float control,size_t length) noexcept {
    length=std::clamp(length,size_t{8},band.capture.size());
    if(!band.recording||band.length!=length) {band.recording=true;band.length=length;band.captured=0;band.position=0;}
    if(band.captured<length) {band.capture[band.captured++]=input;return input;}
    const auto i=static_cast<size_t>(band.position);
    const float fade=std::min(1.f,static_cast<float>(i)/16)*std::min(1.f,static_cast<float>(length-i)/16);
    const auto wet=band.capture[i]*fade;
    band.position+=1;if(band.position>=length)band.position=0;
    return mix(input,wet,std::min(1.f,control*8));
}
Stereo Isolator::process(Stereo input,const std::array<float,3>& controls,double beat) noexcept {
    lowState=lowState+(input-lowState)*lowAlpha;highState=highState+(input-highState)*highAlpha;
    std::array<Stereo,3> split{lowState,highState-lowState,input-highState};
    if(settings.mode!=1) {
        const auto first=lowCrossover[0].process(input);
        const auto low=lowCrossover[1].process(first.low).low;
        const auto midHigh=lowCrossover[2].process(first.high).high;
        const auto mid=highCrossover[1].process(highCrossover[0].process(midHigh).low).low;
        const auto high=highCrossover[3].process(highCrossover[2].process(input).high).high;
        // The reference sums these branches directly; adding phase compensation
        // to low/high would change its measured centre-position response.
        split={low,mid,high};
    }
    if(storageLoaned){++frame;return input;}
    Stereo result=settings.mode==1?cut(input,controls):Stereo{};
    for(size_t b=0;b<3;++b) {
        auto& band=bands[b];const float k=std::clamp(controls[b],-1.f,1.f);const auto dry=split[b];
        if(settings.mode==1) {
            if(k>0) {
                const auto pattern=static_cast<size_t>(std::clamp(settings.addPattern[b],0,2));
                for(size_t tap=0;tap<4;++tap) result=result+band.history.read(rate*secondsPerBeat*addTimes[pattern][tap])*(k*.55f*std::pow(.72f,static_cast<float>(tap)));
            }
        } else if(settings.mode==0) result=result+dry*gain(k,settings.minimum[b],settings.maximum[b]);
        else if(settings.mode==2) {
            const auto zone=std::min(size_t{4},static_cast<size_t>(std::abs(k)*5));
            const auto pattern=static_cast<size_t>(std::clamp(k<0?settings.transPattern[b]:settings.rollPattern[b],0,2));
            const double division=rollTimes[pattern][zone];
            if(k<0) {
                band.recording=false;
                const double phase=wrap(beat/division);
                const float target=phase<.5?1.f:1-std::min(1.f,-k*8);
                band.transGain+=(target-band.transGain)*transSlew;
                result=result+dry*band.transGain;
            } else if(k>.002f) result=result+roll(band,dry,k,static_cast<size_t>(rate*secondsPerBeat*division));
            else {band.recording=false;result=result+dry;}
        } else {
            band.recording=false;const float magnitude=peak(dry);
            band.envelope+=(magnitude-band.envelope)*(magnitude>band.envelope?attack:release);
            Stereo wet=dry;
            if(k<0) {
                const float threshold=-k*.2f*strengths[std::clamp(settings.gateDepth[b],0,2)];
                const float target=band.envelope>=threshold?1.f:0.f;
                band.gate+=(target-band.gate)*(target>band.gate?gateAttack:gateRelease);
                wet=dry*band.gate;
            } else if(k>0) {
                const float drive=1+k*12*strengths[std::clamp(settings.driveDepth[b],0,2)];
                wet={std::tanh(dry.l*drive)/std::sqrt(drive),std::tanh(dry.r*drive)/std::sqrt(drive)};
            }
            result=result+wet;
        }
        if(settings.mode!=2||k<=0)band.recording=false;
        band.history.push(dry);
    }
    ++frame;return result;
}
}
