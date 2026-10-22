#pragma once
#include "Dsp.h"
#include <array>
#include <span>
#include <utility>

namespace rmx {
namespace sample_reader {
constexpr unsigned taps=64,phases=32,levels=33;
constexpr double pi=3.14159265358979323846;
// Compile-time trig keeps the immutable interpolation table in read-only storage
// (flash on the embedded target), with no lazy initialization in the callback.
constexpr double sine(double x) {
    x-=static_cast<long>(x/(2*pi))*(2*pi);
    if(x>pi)x-=2*pi;
    if(x<-pi)x+=2*pi;
    if(x>pi/2)x=pi-x;
    if(x<-pi/2)x=-pi-x;
    const double square=x*x;
    return x*(1+square*(-1./6+square*(1./120+square*(-1./5040+square*(1./362880-square/39916800)))));
}
constexpr double cosine(double x) {return sine(x+pi/2);}
constexpr double quarterOctave=.8408964152537145;
struct Kernel {std::array<float,taps> weights{};};
struct Level {
    float cutoff{};
    std::array<Kernel,phases+1> kernels{};
};
consteval Level makeLevel(unsigned index) {
    Level level;
    double cutoff=.84;
    for(unsigned i=0;i<index;++i)cutoff*=quarterOctave;
    level.cutoff=static_cast<float>(cutoff);
    for(unsigned phase=0;phase<=phases;++phase) {
        const double fraction=double(phase)/phases;double sum=0;
        for(unsigned tap=0;tap<taps;++tap) {
            const double x=double(tap)-double(taps/2-1)-fraction;
            const double window=.42+.5*cosine(pi*x/(taps/2))+.08*cosine(2*pi*x/(taps/2));
            const double a=pi*x*cutoff;
            const double weight=cutoff*(a==0?1:sine(a)/a)*window;
            level.kernels[phase].weights[tap]=static_cast<float>(weight);sum+=weight;
        }
        for(auto& weight:level.kernels[phase].weights)weight/=static_cast<float>(sum);
    }
    return level;
}
template<unsigned Index> inline constexpr Level kernelLevel=makeLevel(Index);
template<size_t... Index> consteval auto makeTable(std::index_sequence<Index...>) {
    return std::array<const Level*,sizeof...(Index)>{&kernelLevel<Index>...};
}
inline constexpr auto table=makeTable(std::make_index_sequence<levels>{});
}

// Faster-than-unity reads use a centered low-pass windowed sinc. Resident
// source data needs no lookahead buffer or playback latency. Slower reads use
// cubic interpolation; integer unity playback remains bit-exact.
inline Stereo readOneShot(std::span<const Stereo> frames,double position,double step) noexcept {
    using namespace sample_reader;
    if(frames.empty()||!std::isfinite(position)||position<0||position>=frames.size())return {};
    const auto index=static_cast<size_t>(position);
    const double fraction=position-index;
    if(std::abs(step-1)<1.e-10&&fraction<1.e-10)return frames[index];
    if(step<=1) {
        const auto at=[&](std::ptrdiff_t i) {return i<0||static_cast<size_t>(i)>=frames.size()?Stereo{}:frames[static_cast<size_t>(i)];};
        const auto i=static_cast<std::ptrdiff_t>(index);
        const Stereo a=at(i-1),b=at(i),c=at(i+1),d=at(i+2);
        const float t=static_cast<float>(fraction);
        return b+((c-a)+(a*2-b*5+c*4-d)*t+((b-c)*3+d-a)*(t*t))*(t*.5f);
    }
    const float cutoff=.84f/static_cast<float>(std::max(1.,step));
    unsigned lower=0;
    while(lower+1<levels&&table[lower+1]->cutoff>cutoff)++lower;
    const unsigned upper=std::min(lower+1,levels-1);
    const float blend=std::clamp((table[lower]->cutoff-cutoff)/std::max(1.e-9f,table[lower]->cutoff-table[upper]->cutoff),0.f,1.f);
    const double phasePosition=fraction*phases;
    const auto phase=std::min(static_cast<unsigned>(phasePosition),phases-1);
    const float between=static_cast<float>(phasePosition-phase);
    Stereo output{};
    for(unsigned tap=0;tap<taps;++tap) {
        const auto source=static_cast<std::ptrdiff_t>(index)+tap-static_cast<std::ptrdiff_t>(taps/2-1);
        if(source<0||static_cast<size_t>(source)>=frames.size())continue;
        const float first=std::lerp(table[lower]->kernels[phase].weights[tap],table[lower]->kernels[phase+1].weights[tap],between);
        const float second=std::lerp(table[upper]->kernels[phase].weights[tap],table[upper]->kernels[phase+1].weights[tap],between);
        output=output+frames[static_cast<size_t>(source)]*std::lerp(first,second,blend);
    }
    return output;
}
}
