#include "HatResearch.h"
#include <algorithm>
#include <bit>
#include <cmath>
namespace rmx::research {
namespace {
float curve60(float x) noexcept {
    const float x2=x*x;
    const float lower=x2*15.959220886230469f+x*-7.762783050537109f;
    return std::max(0.f,(lower*x2+(x*-.02741945907473564f+x2*1.658493161201477f))
        +(x2*x2)*(x*-15.844939231872559f+x2*7.01572322845459f));
}
float pulse(float& phase,float frequency) noexcept {
    const float y=phase<.25f?.75f:-.25f;
    phase+=frequency*(1.f/48000.f);if(phase>1)phase-=1;return y;
}
}
float HatResearch::Envelope::advance() noexcept {
    if(rising){
        value=position;position+=16*(1.f/(.002f*48000.f));
        if(position>1){position=0;value=1;rising=false;falling=true;}
    }
    if(falling){value+=16*(-1.f/(decay*48000.f));if(value<0){value=0;rising=falling=false;}}
    return value;
}
float HatResearch::Biquad::tick(float x) noexcept {
    const auto& c=coefficients;const double y=c[0]*static_cast<double>(x)+s1;
    s1=c[1]*static_cast<double>(x)-c[3]*y+s2;s2=c[2]*static_cast<double>(x)-c[4]*y;
    return static_cast<float>(y);
}
void HatResearch::start() noexcept {
    phase.fill(0);random1=0x77332244;random2=0xefcdab89;
    main.start();attack.start();highpass1.clear();highpass2.clear();gain=1;state=1;
}
void HatResearch::block() noexcept {
    if(requested){if(!state)start();else if(state==1)state=2;requested=false;}
    if(state>=7)start();
    const float gainStep=state>=2?-.00625f:0;if(state>=2)++state;
    if(!state)pending.fill(0);
    else for(size_t begin=0;begin<32;begin+=16){
        float n=main.advance(),a=attack.advance();
        if(!main.rising){n=curve60(n);a=curve60(a);}
        n=std::min(1.f,n*1.3f)*.15f;a=std::min(1.f,a*1.3f)*.162f;
        for(size_t i=begin;i<begin+16;++i){
            const float p1=pulse(phase[0],800),p2=pulse(phase[1],525),p3=pulse(phase[2],370),p4=pulse(phase[3],205);
            const float pulses=highpass1.tick(((p1+p2)+p3)+p4);
            random1^=random2;const float white=static_cast<float>(std::bit_cast<int32_t>(random2))*(1.f/2147483648.f);random2+=random1;
            const float mixed=highpass2.tick(white*n+pulses*a);
            gain+=gainStep;
            pending[i]=static_cast<float>(static_cast<double>((mixed*.4466835856437683f)*gain)*6.91373157);
        }
    }
    if(!main.rising&&main.value==0&&std::abs(pending.back())<1e-9f)state=0;
    for(auto& sample:pending){startupGain=std::min(1.f,startupGain+.00625f);sample*=startupGain;}
}
void HatResearch::process(std::span<float> output) noexcept {
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
