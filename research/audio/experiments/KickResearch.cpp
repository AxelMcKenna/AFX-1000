#include "KickResearch.h"
#include "KickResearchCalibration.h"
#include <algorithm>
#include <bit>
#include <cmath>
namespace rmx::research {
namespace {
float polynomial(const std::array<float,7>& coefficients,float x) noexcept {
    float y=coefficients.back();for(size_t i=6;i>0;--i)y=y*x+coefficients[i-1];return y;
}
float amplitude(float x) noexcept {
    const float x2=x*x;
    return (x*21.773086547851562f+x2*(x*264.4794616699219f-124.14238739013672f))
        +(x2*x2)*(x*89.11289978027344f-250.22425842285156f);
}
float pitchCurve(float x) noexcept {return x<.6683400273323059f?0:amplitude(x);}
float toneCurve(float x) noexcept {
    const float x2=x*x;
    return (x*.04121410846710205f+x2*.7498405575752258f)+x2*(x2*2.026017665863037f+x*-1.8232481479644775f);
}
float triangle(float& phase,float frequency) noexcept {
    const float x=phase*4;const float y=phase>.5f?3-x:x-1;
    phase+=frequency*(1.f/48000.f);if(phase>1)phase-=1;return y;
}
}
float KickResearch::Envelope::advance() noexcept {
    if(rising){
        value=position;position+=16*(1.f/(attack*48000.f));
        if(position>1){position=0;value=1;rising=false;falling=true;}
    }
    if(falling){value+=16*(-1.f/(decay*48000.f));if(value<0){value=0;rising=falling=false;}}
    return value;
}
float KickResearch::Biquad::tick(float x) noexcept {
    const auto& c=coefficients;const double y=c[0]*static_cast<double>(x)+s1;
    s1=c[1]*static_cast<double>(x)-c[3]*y+s2;s2=c[2]*static_cast<double>(x)-c[4]*y;
    return static_cast<float>(y);
}
void KickResearch::start() noexcept {
    phase1=phase2=.25f;random1=0x1f9f4541;random2=0x93a6ff6c;
    tone.start();pitch.start();noise.start();bandpass.clear();highpass.clear();gain=1;state=1;
}
void KickResearch::block() noexcept {
    if(requested){if(!state)start();else if(state==1)state=2;requested=false;}
    if(state>=7)start();
    const float gainStep=state>=2?-.00625f:0;if(state>=2)++state;
    if(!state)pending.fill(0);
    else for(size_t begin=0;begin<32;begin+=16){
        const float frequency=49.91f+(49.91f*6-49.91f)*pitchCurve(pitch.advance());
        const float level=std::min(.3f,toneCurve(tone.advance()))*.07227f;
        const float s=polynomial(kickSineHz,frequency),c=polynomial(kickCosineHz,frequency);
        const float alpha=s*.5f,scale=1.f/(1+alpha),b=alpha*scale;
        bandpass.coefficients={b,0,-b,(-2*c)*scale,(1-alpha)*scale};
        const float hiss=pitchCurve(noise.advance());
        for(size_t i=begin;i<begin+16;++i){
            const float a=triangle(phase1,frequency)*23;const float b=triangle(phase2,frequency*.6f)*3;
            const float pitched=bandpass.tick((a+b)*level);
            random1^=random2;const float white=static_cast<float>(std::bit_cast<int32_t>(random2))*(1.f/2147483648.f);random2+=random1;
            const float mixed=(pitched+(white*hiss)*.04f)*.223872110247612f;
            const float sample=highpass.tick(mixed);gain+=gainStep;
            pending[i]=static_cast<float>(static_cast<double>(sample*gain)*6.91373157);
        }
    }
    if(!tone.rising&&tone.value==0&&std::abs(pending.back())<1e-9f)state=0;
    // Global output fade advances on the generated clock, including silence.
    // Applying it after FIFO emission would make callback fragments incorrect.
    for(auto& sample:pending){startupGain=std::min(1.f,startupGain+.00625f);sample*=startupGain;}
}
void KickResearch::process(std::span<float> output) noexcept {
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
