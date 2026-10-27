#include "ClapResearch.h"
#include <algorithm>
#include <bit>
#include <cmath>
namespace rmx::research {
float ClapResearch::Envelope::advance() noexcept {
    if(rising){
        value=position;position+=16*(1.f/(.016f*48000.f));
        if(position>1){position=0;value=1;rising=false;falling=true;}
    }
    if(falling){value+=16*(-1.f/(decay*48000.f));if(value<0){value=0;rising=falling=false;}}
    return value;
}
float ClapResearch::Biquad::tick(float x) noexcept {
    const auto& c=coefficients;const double y=c[0]*static_cast<double>(x)+s1;
    s1=c[1]*static_cast<double>(x)-c[3]*y+s2;s2=c[2]*static_cast<double>(x)-c[4]*y;
    return static_cast<float>(y);
}
void ClapResearch::start() noexcept {
    phase=1;elapsed=0;random1=0xb741fe44;random2=0x2c342f89;
    noise.start();tail.start();bandpass.clear();highpass.clear();lowpass1.state=0;gain=1;state=1;
}
void ClapResearch::block() noexcept {
    if(requested){if(!state)start();else if(state==1)state=2;requested=false;}
    if(state>=7)start();
    const float gainStep=state>=2?-.00625f:0;if(state>=2)++state;
    if(!state)pending.fill(0);
    else for(size_t begin=0;begin<32;begin+=16){
        float n=noise.advance();n*=n;n*=n;
        const bool burst=elapsed<static_cast<unsigned>(.031f*48000.f);
        if(elapsed<0x7ffeffff)elapsed+=16;
        float t=tail.advance();t*=t;t*=t;
        for(size_t i=begin;i<begin+16;++i){
            const float saw=phase;phase-=91.f*(1.f/48000.f);if(phase<0)phase=1;
            random1^=random2;const float white=static_cast<float>(std::bit_cast<int32_t>(random2))*(1.f/2147483648.f);random2+=random1;
            const float filtered=bandpass.tick(white),low=lowpass1.tick(filtered),high=highpass.tick(filtered);
            const float mixed=burst?saw*high:(low*t)*.075f+(high*n)*.8f;
            const float clipped=std::clamp(mixed,-.218871608376503f,.218871608376503f);
            gain+=gainStep;
            pending[i]=static_cast<float>(static_cast<double>((clipped*.3981071710586548f)*gain)*6.91373157);
        }
    }
    if(!tail.rising&&tail.value==0&&std::abs(pending.back())<1e-9f)state=0;
    for(auto& sample:pending){startupGain=std::min(1.f,startupGain+.00625f);sample*=startupGain;}
}
void ClapResearch::process(std::span<float> output) noexcept {
    if(!output.empty())processingStarted=true;
    std::fill(output.begin(),output.end(),0);size_t read=0,written=0;
    while(read<output.size()){
        const auto take=std::min(32-received,output.size()-read);read+=take;received+=take;
        const auto emit=std::min(available,output.size()-written);
        std::copy_n(pending.begin()+static_cast<std::ptrdiff_t>(head),emit,output.begin()+static_cast<std::ptrdiff_t>(written));
        written+=emit;available-=emit;head+=emit;
        if(received==32){block();received=0;available=32;head=0;}
    }
}
}
