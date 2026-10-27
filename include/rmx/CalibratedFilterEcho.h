#pragma once
#include "Dsp.h"
#include "FilterEchoCalibration.h"
#include "FactoryEchoReturn.h"
#include <array>

namespace rmx {
// Static 48 kHz factory Normal-width model identified from public I/O.
// Moving controls, other profiles/rates and effect-to-effect tails remain
// separate validation work. All delay storage is allocated in prepare().
class CalibratedFilterEcho {
public:
    void prepare(double rate) {
        echoReturn.prepare(rate);
        reset();
    }
    void reset() noexcept {
        echoReturn.reset();
        clearFilters();age=0;lastType=lastRaw=-1;sharedStartup=false;
    }
    void invalidate() noexcept {lastType=-1;}
    Stereo process(Stereo input,int type,int raw,int timeRaw,float enabled,double bpm,float startup=1,bool priming=false) noexcept {
        raw=std::clamp(raw,0,255);timeRaw=std::clamp(timeRaw,0,255);
        if(type!=lastType) {
            clearFilters();age=0;lastType=type;lastRaw=-1;
            echoReturn.restart(type==7?FactoryEchoReturn::Profile::crush:FactoryEchoReturn::Profile::filter);
        }
        if(raw!=lastRaw) {configure(type,raw);lastRaw=raw;}
        if(priming){
            // The common source clock precedes this effect's first active
            // block. Its private filter/return history is still silent.
            sharedStartup=true;++age;return input;
        }
        const double original[]{input.l,input.r};double direct[2]{},feed[2]{};
        if(type==7) {
            const auto heldInput=sharedStartup?input*startup:input;
            // The reference's settled hold clock starts 32 input frames into
            // a new instance. Preserve its fractional period and strict test;
            // rounding to integer intervals audibly changes the aliased signal.
            if(age<32)held=heldInput;
            else {
                holdCounter-=1;
                if(holdCounter<0) {
                    // Activation's first hold interval retains the reset
                    // sample. Subsequent fractional-clock captures refresh it.
                    if(!(sharedStartup&&age==32&&holdPeriod>1))held=heldInput;
                    holdCounter+=holdPeriod;
                }
            }
        }
        for(unsigned channel=0;channel<2;++channel) {
            const double x=original[channel];
            if(type==0) {
                auto& s=bandState[channel];
                const double y=band.b0*(x-s[1])-band.a1*s[2]-band.a2*s[3]-band.a3*s[4];
                s[1]=s[0];s[0]=x;s[4]=s[3];s[3]=s[2];s[2]=y;
                direct[channel]=x+y;feed[channel]=x+.85*y;
            } else {
                const double u=(type==7?(channel==0?held.l:held.r):x)+resonance*feedbackState[channel];
                const double y=main[channel].tick(u),b=feedbackBand[channel].tick(u);
                const double f=feedbackGain*b+feedbackPoleState[channel];
                feedbackPoleState[channel]=(type==5||type==7?-feedbackGain:feedbackGain)*b+feedbackPole*f;
                feedbackState[channel]=f;
                direct[channel]=feed[channel]=x+(y-x)*gain;
            }
        }
        if(startup!=1){
            const double dry=type==0?1:1-gain;
            for(unsigned channel=0;channel<2;++channel){
                const double base=original[channel]*dry;
                direct[channel]=base+(direct[channel]-base)*startup;
                feed[channel]=base+(feed[channel]-base)*startup;
                if(type==7&&sharedStartup){
                    direct[channel]=base+(direct[channel]-base)*startup;
                    // Crush's unfiltered return blend uses the input fade too.
                    feed[channel]=base*startup+(feed[channel]-base);
                }
            }
        }
        const float activation=std::clamp((raw-4)/5.f,0.f,1.f)*enabled;
        const float returnGain=startup*startup;
        const auto tail=echoReturn.process({feed[0],feed[1]},timeRaw,activation,bpm,sharedStartup?returnGain:1,sharedStartup);
        ++age;
        return {static_cast<float>(original[0]+(direct[0]-original[0])*enabled+tail[0]),
                static_cast<float>(original[1]+(direct[1]-original[1])*enabled+tail[1])};
    }
private:
    struct Biquad {
        double b0{},b1{},b2{},a1{},a2{},s1{},s2{};
        void configure(double hz,double rate,bool high) noexcept {
            const double w=2*std::numbers::pi*hz/rate,alpha=std::sin(w)/std::sqrt(2.);
            a1=-2*std::cos(w)/(1+alpha);a2=(1-alpha)/(1+alpha);
            b0=(1+(high?-a1:a1)+a2)/4;b1=(high?-2:2)*b0;b2=b0;
        }
        double tick(double x) noexcept {const double y=b0*x+s1;s1=b1*x-a1*y+s2;s2=b2*x-a2*y;return y;}
        void reset() noexcept {s1=s2=0;}
    };
    static double value(const FilterEchoPoint& p,unsigned column) noexcept {return column==0?p.cutoffRatio:p.resonance;}
    template<size_t N> static double interpolate(const std::array<FilterEchoPoint,N>& points,int raw,unsigned column) noexcept {
        size_t i=0;while(i+2<N&&raw>points[i+1].raw)++i;
        const auto segment=[&](size_t j) {return (value(points[j+1],column)-value(points[j],column))/(points[j+1].raw-points[j].raw);};
        const auto slope=[&](size_t j) {
            if(j==0||j+1==N) {
                const size_t a=j==0?0:N-2,b=j==0?1:a-1;
                const double h0=points[a+1].raw-points[a].raw,h1=points[b+1].raw-points[b].raw,d0=segment(a),d1=segment(b);
                const double result=((2*h0+h1)*d0-h0*d1)/(h0+h1);
                return result*d0<=0?0.:d0*d1<=0&&std::abs(result)>3*std::abs(d0)?3*d0:result;
            }
            const double d0=segment(j-1),d1=segment(j);if(d0*d1<=0)return 0.;
            const double h0=points[j].raw-points[j-1].raw,h1=points[j+1].raw-points[j].raw,w1=2*h1+h0,w2=h1+2*h0;
            return (w1+w2)/(w1/d0+w2/d1);
        };
        const double h=points[i+1].raw-points[i].raw,t=(raw-points[i].raw)/h,t2=t*t,t3=t2*t;
        return (2*t3-3*t2+1)*value(points[i],column)+(t3-2*t2+t)*h*slope(i)
            +(-2*t3+3*t2)*value(points[i+1],column)+(t3-t2)*h*slope(i+1);
    }
    void configure(int type,int raw) noexcept {
        if(type==0) {band=bandEchoCalibration[static_cast<size_t>(raw)];return;}
        const bool high=type==5||type==7;
        double ratio=1;
        const auto profile=[&](const auto& points) {ratio=interpolate(points,raw,0);resonance=interpolate(points,raw,1);};
        if(high)profile(hpfEchoCalibration);else profile(lpfEchoCalibration);
        const double fc=type==7?std::round(60*std::exp(std::max(raw-4,0)*.0168583737)):
            (high?60*std::pow(10000./60,std::max(raw-4,0)/251.):96*std::pow(23500./96,(255-std::max(raw,4))/251.))*ratio;
        gain=1-std::pow(std::clamp(type==7?(129-raw)/126.:(66-raw)/63.,0.,1.),2);
        // Preserve both roundings: the scaled control, then the following
        // interval boundary. At low controls adding one crosses an exponent
        // boundary; omitting that rounding changes recurring capture frames.
        const float scaled=raw*24.f;
        const float boundary=scaled*(1.f/255.f)+1.f;
        holdPeriod=std::max(1.f,boundary-1.f);
        const double t=std::tan(std::numbers::pi*fc/48000);
        feedbackPole=(1-t)/(1+t);feedbackGain=(1+(high?feedbackPole:-feedbackPole))/2;
        for(unsigned channel=0;channel<2;++channel) {
            main[channel].configure(fc,48000,high);
            auto& b=feedbackBand[channel];b.a1=main[channel].a1;b.a2=main[channel].a2;
            b.b0=(1-b.a2)/2;b.b1=0;b.b2=-b.b0;
        }
    }
    void clearFilters() noexcept {
        bandState={};feedbackState={};feedbackPoleState={};held={};holdCounter=0;
        for(auto& f:main)f.reset();for(auto& f:feedbackBand)f.reset();
    }
    FactoryEchoReturn echoReturn;
    std::array<Biquad,2> main,feedbackBand;
    std::array<std::array<double,5>,2> bandState{};
    std::array<double,2> feedbackState{},feedbackPoleState{};
    BandEchoPoint band{};double feedbackPole{},feedbackGain{},resonance{},gain{};
    Stereo held{};double holdCounter{},holdPeriod{1};
    uint64_t age{};int lastType{-1},lastRaw{-1};bool sharedStartup{};
};
}
