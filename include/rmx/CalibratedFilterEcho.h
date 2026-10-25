#pragma once
#include "Dsp.h"
#include "FilterEchoCalibration.h"
#include <array>

namespace rmx {
// Static 48 kHz factory Normal-width model identified from public I/O.
// Moving controls, other profiles/rates and effect-to-effect tails remain
// separate validation work. All delay storage is allocated in prepare().
class CalibratedFilterEcho {
public:
    void prepare(double rate) {
        for(auto& line:lines)line.prepare(static_cast<size_t>(rate*1.5)+4);
        for(auto& channel:returns)for(auto& filter:channel)filter.configure(283.99944,rate,true);
        reset();
    }
    void reset() noexcept {
        for(auto& line:lines)line.reset();
        clearFilters();age=0;lastType=lastRaw=-1;
    }
    void invalidate() noexcept {lastType=-1;}
    Stereo process(Stereo input,int type,int raw,int timeRaw,float enabled,double bpm) noexcept {
        raw=std::clamp(raw,0,255);timeRaw=std::clamp(timeRaw,0,255);
        if(type!=lastType) {clearFilters();age=0;lastType=type;lastRaw=-1;}
        if(raw!=lastRaw) {configure(type,raw);lastRaw=raw;}
        const double original[]{input.l,input.r};double direct[2]{},feed[2]{};
        for(unsigned channel=0;channel<2;++channel) {
            const double x=original[channel];
            if(type==0) {
                auto& s=bandState[channel];
                const double y=band.b0*(x-s[1])-band.a1*s[2]-band.a2*s[3]-band.a3*s[4];
                s[1]=s[0];s[0]=x;s[4]=s[3];s[3]=s[2];s[2]=y;
                direct[channel]=x+y;feed[channel]=x+.85*y;
            } else {
                const double u=x+resonance*feedbackState[channel];
                const double y=main[channel].tick(u),b=feedbackBand[channel].tick(u);
                const double f=feedbackGain*b+feedbackPoleState[channel];
                feedbackPoleState[channel]=(type==5?-feedbackGain:feedbackGain)*b+feedbackPole*f;
                feedbackState[channel]=f;
                direct[channel]=feed[channel]=x+(y-x)*gain;
            }
        }
        std::array<float,4> weights{};
        const float position=std::clamp((timeRaw-3)/62.25f,0.f,4.f);
        const unsigned upper=std::min(3u,static_cast<unsigned>(position));
        if(upper>0)weights[upper-1]=upper+1-position;
        weights[upper]=position-upper;
        if(position==4)weights[3]=1;
        const double beat=48*std::floor(60000/std::clamp(bpm,40.,240.));
        Stereo returned{};
        const float activation=std::clamp((raw-4)/5.f,0.f,1.f)*enabled;
        for(size_t i=0;i<lines.size();++i) {
            const double delay=beat*(i+1)*.25;
            const auto tap=age>=static_cast<uint64_t>(delay)?lines[i].read(delay):Stereo{};
            returned=returned+tap*weights[i];
            lines[i].push({static_cast<float>(std::clamp(feed[0]*activation+tap.l*.75,-8.,8.)),
                           static_cast<float>(std::clamp(feed[1]*activation+tap.r*.75,-8.,8.))});
        }
        ++age;
        const double tail[]{returns[0][1].tick(returns[0][0].tick(returned.l)),
                            returns[1][1].tick(returns[1][0].tick(returned.r))};
        return {static_cast<float>(original[0]+(direct[0]-original[0])*enabled+tail[0]*.7),
                static_cast<float>(original[1]+(direct[1]-original[1])*enabled+tail[1]*.7)};
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
        const bool high=type==5;
        double ratio=1;
        const auto profile=[&](const auto& points) {ratio=interpolate(points,raw,0);resonance=interpolate(points,raw,1);};
        if(high)profile(hpfEchoCalibration);else profile(lpfEchoCalibration);
        const double fc=(high?60*std::pow(10000./60,std::max(raw-4,0)/251.):96*std::pow(23500./96,(255-std::max(raw,4))/251.))*ratio;
        gain=1-std::pow(std::clamp((66-raw)/63.,0.,1.),2);
        const double t=std::tan(std::numbers::pi*fc/48000);
        feedbackPole=(1-t)/(1+t);feedbackGain=(1+(high?feedbackPole:-feedbackPole))/2;
        for(unsigned channel=0;channel<2;++channel) {
            main[channel].configure(fc,48000,high);
            auto& b=feedbackBand[channel];b.a1=main[channel].a1;b.a2=main[channel].a2;
            b.b0=(1-b.a2)/2;b.b1=0;b.b2=-b.b0;
        }
    }
    void clearFilters() noexcept {
        bandState={};feedbackState={};feedbackPoleState={};
        for(auto& f:main)f.reset();for(auto& f:feedbackBand)f.reset();
        for(auto& channel:returns)for(auto& f:channel)f.reset();
    }
    std::array<FractionalDelay,4> lines;
    std::array<Biquad,2> main,feedbackBand;
    std::array<std::array<Biquad,2>,2> returns;
    std::array<std::array<double,5>,2> bandState{};
    std::array<double,2> feedbackState{},feedbackPoleState{};
    BandEchoPoint band{};double feedbackPole{},feedbackGain{},resonance{},gain{};
    uint64_t age{};int lastType{-1},lastRaw{-1};
};
}
