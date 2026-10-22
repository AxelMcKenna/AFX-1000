#pragma once
#include "Sample.h"
#include <numbers>

namespace rmx {
// Original synthesized assets, rendered before audio starts. These are project
// voicings, not extracted recordings or a claim of factory RMX sound matching.
inline Sample makeDrumSample(unsigned type,unsigned variation,double rate) {
    constexpr double pi=std::numbers::pi;
    Sample sample;sample.rate=rate;
    constexpr double lengths[]{1.2,.9,.9,.45};
    sample.frames.resize(static_cast<size_t>(rate*lengths[type%4]));
    StateFilter tone,air,bodyFilter;
    tone.configure(type==1?2100.f:type==2?1400.f:7200.f,type==2?.85f:.7f,rate);
    air.configure(type==3?12500.f:9500.f,.7071f,rate);
    bodyFilter.configure(type==3?4300.f:4500.f,.7071f,rate);
    uint32_t random=0x749abcu+type+variation*113u;
    double phase=0;float dc=0,maximum=0;
    const float dcAlpha=poleCoefficient(5,rate);
    const double tuning=std::pow(2.,variation*.6/12.);
    constexpr double metalHz[]{3180,4370,5783,7190,8910,10980};
    for(size_t i=0;i<sample.frames.size();++i) {
        const double t=i/rate;
        random^=random<<13;random^=random>>17;random^=random<<5;
        const float noise=static_cast<float>(static_cast<int32_t>(random))/2147483648.f;
        const float band=tone.process({noise,noise}).band.l;
        const float bright=air.process({band,band}).low.l;
        double value=0;
        if(type==0) {
            phase+=2*pi*tuning*(49+102*std::exp(-t*65)+32*std::exp(-t*310))/rate;
            const double body=std::tanh(1.7*std::sin(phase))*.68*std::exp(-t*(9+variation*.35));
            const double click=bodyFilter.process({noise,noise}).high.l*.20*std::exp(-t*480);
            value=(body+click)*(1-std::exp(-t*4500));
        } else if(type==1) {
            const double shell=.30*std::sin(2*pi*178*t*tuning)*std::exp(-t*31)
                +.13*std::sin(2*pi*337*t*tuning+.2)*std::exp(-t*43)
                +.055*std::sin(2*pi*487*t*tuning)*std::exp(-t*57);
            const double wires=bright*(1-std::exp(-t*3000))*(1.35*std::exp(-t*15)+.35*std::exp(-t*95));
            value=shell+wires;
        } else if(type==2) {
            double bursts=0;
            for(double onset:{0.,.009,.018})if(t>=onset)bursts+=std::exp(-(t-onset)/.0028);
            const double tail=t<.024?0:(1-std::exp(-(t-.024)*1800))*std::exp(-(t-.024)*12);
            value=bright*(bursts*1.3+tail*.80);
        } else {
            double metal=0;
            for(unsigned partial=0;partial<6;++partial) {
                const double hz=metalHz[partial]*tuning;
                if(hz<rate*.44)metal+=std::sin(2*pi*hz*t+partial*.71)*std::exp(-t*(27+partial*2.1));
            }
            const float ringing=bodyFilter.process({static_cast<float>(metal*.115),static_cast<float>(metal*.115)}).high.l;
            value=ringing+bright*(.85*std::exp(-t*38)+.45*std::exp(-t*180));
            value*=1-std::exp(-t*6000);
        }
        dc+=(static_cast<float>(value)-dc)*dcAlpha;
        float result=static_cast<float>(value)-dc;
        // Short end taper only: keep the synthesized attack intact.
        result*=std::min(1.f,static_cast<float>(sample.frames.size()-1-i)/64.f);
        sample.frames[i]={result,result};maximum=std::max(maximum,std::abs(result));
    }
    constexpr float peaks[]{.86f,.80f,.76f,.63f};
    const float gain=peaks[type%4]/std::max(maximum,1.e-9f);
    for(auto& frame:sample.frames)frame=frame*gain;
    return sample;
}
}
