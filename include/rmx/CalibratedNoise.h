#pragma once
#include "Dsp.h"
#include "NoiseCalibration.h"

namespace rmx {
// A measured linear filter model. Excitation remains original project noise;
// no recorded reference audio or manufacturer random generator is embedded.
class CalibratedNoise {
public:
    void reset() noexcept { x1=x2=y1=y2=y3={};lastRaw=-1; }
    void configure(int raw,int width=1) noexcept {
        raw=std::clamp(raw,0,255);
        width=std::clamp(width,0,2);
        const int key=raw+256*width;
        if(key==lastRaw)return;
        lastRaw=key;
        size_t i=0;
        while(i+2<noiseCalibration.size()&&raw>noiseCalibration[i+1].raw)++i;
        const float h=noiseCalibration[i+1].raw-noiseCalibration[i].raw;
        const float t=(raw-noiseCalibration[i].raw)/h,t2=t*t,t3=t2*t;
        for(unsigned column=0;column<4;++column) {
            coefficients[column]=(2*t3-3*t2+1)*value(i,column)+(t3-2*t2+t)*h*slope(i,column)
                +(-2*t3+3*t2)*value(i+1,column)+(t3-t2)*h*slope(i+1,column);
        }
        if(width!=1){
            // The reference's unmodulated sweep advances the visible control
            // by50 before deriving the two bilinear band edges. Mild/Wild
            // use different edge trajectories, with the same feedback law.
            const int position=std::min(raw+50,255);
            const double ratio=width==0?.75f:2.f;
            const double edgeStep=width==0?.9932088255882263f:.9825870990753174f;
            const double base=width==0?35.f:80.f;
            const double frequencyStep=width==0?1.01789128780365f:1.0199010372161865f;
            const double spread=ratio*(position>=234?std::pow(edgeStep,position-234):1);
            const double low=base*std::pow(frequencyStep,position-4);
            const double high=low*(spread+.5)/(spread-.5);
            constexpr double pi=3.14159265358979323846;
            const double a=std::tan(pi*low/48000),b=std::tan(pi*high/48000);
            const double delta=b-a,product=a*b,inverse=1/(1+delta+product);
            const float numerator=static_cast<float>(delta*inverse);
            float travel=(position-3)*(1.f/252);
            for(unsigned power=0;power<4;++power)travel*=travel;
            const float feedback=.7f+travel*.1f;
            // Preserve the measured excitation/output law while replacing
            // the filter response. No reference audio or generator is used.
            const float referenceNumerator=(1-coefficients[1])*.5f;
            coefficients[3]*=numerator/referenceNumerator;
            coefficients[0]=static_cast<float>((2*product-2)*inverse)-feedback*numerator;
            coefficients[1]=static_cast<float>((1-delta+product)*inverse);
            coefficients[2]=feedback*numerator;
        }
    }
    Stereo process(Stereo white) noexcept {
        const auto output=(white-x2)*coefficients[3]-y1*coefficients[0]-y2*coefficients[1]-y3*coefficients[2];
        x2=x1;x1=white;y3=y2;y2=y1;y1=output;
        return output;
    }
private:
    static constexpr float value(size_t i,unsigned column) noexcept {
        const auto& point=noiseCalibration[i];
        return column==0?point.a1:column==1?point.a2:column==2?point.a3:point.b0;
    }
    static constexpr float slope(size_t i,unsigned column) noexcept {
        const auto segment=[&](size_t n) {
            return (value(n+1,column)-value(n,column))/(noiseCalibration[n+1].raw-noiseCalibration[n].raw);
        };
        if(i==0||i+1==noiseCalibration.size()) {
            const size_t a=i==0?0:noiseCalibration.size()-2,b=i==0?1:a-1;
            const float h0=noiseCalibration[a+1].raw-noiseCalibration[a].raw;
            const float h1=noiseCalibration[b+1].raw-noiseCalibration[b].raw;
            const float d0=segment(a),d1=segment(b);
            const float result=((2*h0+h1)*d0-h0*d1)/(h0+h1);
            if(result*d0<=0)return 0;
            return d0*d1<=0&&std::abs(result)>3*std::abs(d0)?3*d0:result;
        }
        const float d0=segment(i-1),d1=segment(i);
        if(d0*d1<=0)return 0;
        const float h0=noiseCalibration[i].raw-noiseCalibration[i-1].raw;
        const float h1=noiseCalibration[i+1].raw-noiseCalibration[i].raw;
        const float w1=2*h1+h0,w2=h1+2*h0;
        return (w1+w2)/(w1/d0+w2/d1);
    }
    std::array<float,4> coefficients{};
    Stereo x1{},x2{},y1{},y2{},y3{};
    int lastRaw{-1};
};
}
