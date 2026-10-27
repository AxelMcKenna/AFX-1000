#include "rmx/drums/Snare.h"
#include "rmx/drums/Controls.h"
#include <algorithm>
#include <bit>
#include <cmath>
namespace rmx::drums {
namespace {
float curve60(float x) noexcept {
    if(x<=.05f)return 0;
    const float x2=x*x;
    const float lower=x2*11.69431209564209f+x*-4.366483688354492f;
    return (lower*x2+(x*-.02444826252758503f+x2*.7473941445350647f))
        +(x2*x2)*(x*-13.952014923095703f+x2*6.9004926681518555f);
}
float triangle(float& phase,float frequency) noexcept {
    const float x=phase*4;const float y=phase>.5f?3-x:x-1;
    phase+=frequency*(1.f/48000.f);if(phase>1)phase-=1;return y;
}
}
void Snare::setControls(unsigned level,unsigned pitchRaw) noexcept {
    outputLevel.set(level);pitchRatio=drumPitchRate(pitchRaw);
    lowpass.coefficients=drumLowpass(9000*pitchRatio,1);
    const auto lp=drumFirstOrder(9000*pitchRatio,false),hp=drumFirstOrder(10000*pitchRatio,true);
    lowpass1.b0=lp[0];lowpass1.b1=lp[1];lowpass1.feedback=lp[2];
    highpass1.b0=hp[0];highpass1.b1=hp[1];highpass1.feedback=hp[2];
}
float Snare::Envelope::advance() noexcept {
    if(rising){
        value=position;position+=16*(1.f/(.001f*48000.f));
        if(position>1){position=0;value=1;rising=false;falling=true;}
    }
    if(falling){value+=16*(-1.f/(decay*48000.f));if(value<0){value=0;rising=falling=false;}}
    return value;
}
float Snare::Biquad::tick(float x) noexcept {
    const auto& c=coefficients;const double y=c[0]*static_cast<double>(x)+s1;
    s1=c[1]*static_cast<double>(x)-c[3]*y+s2;s2=c[2]*static_cast<double>(x)-c[4]*y;
    return static_cast<float>(y);
}
void Snare::start() noexcept {
    voiceVelocity=nextVelocity;
    phase1=phase2=.25f;random1=0xd0f61b8f;random2=0x34373a95;
    tone.start();pitch.start();noise.start();bandpass.clear();lowpass.clear();lowpass1.state=highpass1.state=0;gain=1;state=1;
}
void Snare::block() noexcept {
    if(requested){if(!state||state==1){nextVelocity=requestedVelocity;if(!state)start();else state=2;}requested=false;}
    if(state>=7)start();
    const float gainStep=state>=2?-.00625f:0;if(state>=2)++state;
    if(!state)pending.fill(0);
    else for(size_t begin=0;begin<32;begin+=16){
        float p=pitch.advance();p*=p;p=p*p+1;
        const float base=168.2f*pitchRatio,frequency=base*p,second=(base+84.8f)*p;
        const float level=std::min(1.f,curve60(tone.advance())*1.3f)*1.3f;
        bandpass.coefficients=drumBandpass(frequency,2.0618555545806885f);
        const float hiss=std::min(.66f,curve60(noise.advance())*1.6667f);
        for(size_t i=begin;i<begin+16;++i){
            const float a=triangle(phase1,frequency),b=triangle(phase2,second);
            const float octaves=(std::abs(a)-.5f)+(std::abs(b)-.5f);
            const float pitched=bandpass.tick(((a+b)*.8f+octaves*.6f)*level);
            random1^=random2;const float white=static_cast<float>(std::bit_cast<int32_t>(random2))*(1.f/2147483648.f);random2+=random1;
            const float filtered=lowpass.tick(highpass1.tick(lowpass1.tick(white)));
            const float mixed=std::clamp(pitched+filtered*hiss,-.7943282127380371f,.7943282127380371f);
            gain+=gainStep;
            pending[i]=static_cast<float>(static_cast<double>((mixed*gain)*.1258925348520279f)*6.91373157);
        }
    }
    if(!noise.rising&&noise.value==0&&std::abs(pending.back())<1e-9f)state=0;
    for(auto& sample:pending){startupGain=std::min(1.f,startupGain+.00625f);sample=((sample*voiceVelocity)*startupGain)*outputLevel.advance();}
}
void Snare::process(std::span<float> output) noexcept {
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
