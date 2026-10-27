#pragma once
#include "rmx/drums/ControlTables.h"
#include "rmx/drums/FrequencyCalibration.h"
#include <algorithm>
namespace rmx::drums {
inline float drumPitchRate(unsigned raw,unsigned left=11,unsigned right=11) noexcept {
    raw=std::min(raw,255u);left=std::min(left,11u);right=std::min(right,11u);
    if(raw>120&&raw<136)return 1;
    const auto& c=raw<=120?drumPitchLeft[left]:drumPitchRight[right];
    const auto n=raw<=120?raw:raw-135;const float x=static_cast<float>(n),x2=static_cast<float>(n*n);
    return x2*(c[0]*x+c[1])+(c[2]*x+c[3]);
}
inline float drumLevel(unsigned raw) noexcept {return drumLevelTable[std::min(raw,255u)];}
struct DrumLevelRamp {
    float value{1},target{1},step{};unsigned remaining{};
    void set(unsigned raw) noexcept {
        const float next=drumLevel(raw);if(next==target)return;
        target=next;step=(target-value)*.00625f;remaining=160;
    }
    float advance() noexcept {
        if(remaining){value+=step;if(!--remaining)value=target;}
        return value;
    }
};
// Measured frequency-polynomial calibration, evaluated in its float32 grouping.
// Coefficient order matters at the moving low-frequency drum resonances.
inline float drumFrequencyPolynomial(const std::array<float,7>& c,float x) noexcept {
    const float x2=x*x,x4=x2*x2;
    return (((c[3]*x+c[4]*x2)*x2+(c[1]*x+c[2]*x2))+(c[5]*x+c[6]*x2)*x4)+c[0];
}
inline std::array<float,5> drumBandpass(float frequency,float q) noexcept {
    const float s=drumFrequencyPolynomial(kickSineHz,frequency),c=drumFrequencyPolynomial(kickCosineHz,frequency);
    const float alpha=s/(q+q),scale=1.f/(1.f+alpha),b=alpha*scale;
    return {b,0,-b,(-2.f*c)*scale,scale-b};
}
inline std::array<float,5> drumHighpass(float frequency,float q) noexcept {
    const float s=drumFrequencyPolynomial(kickSineHz,frequency),c=drumFrequencyPolynomial(kickCosineHz,frequency);
    const float alpha=s/(q+q),scale=1.f/(1.f+alpha),b1=-(1.f+c)*scale,b0=b1*-.5f;
    return {b0,b1,b0,(-2.f*c)*scale,(1.f-alpha)*scale};
}
inline std::array<float,5> drumLowpass(float frequency,float q) noexcept {
    const float s=drumFrequencyPolynomial(kickSineHz,frequency),c=drumFrequencyPolynomial(kickCosineHz,frequency);
    const float alpha=s/(q+q),scale=1.f/(1.f+alpha),b1=(1.f-c)*scale,b0=b1*.5f;
    return {b0,b1,b0,(-2.f*c)*scale,(1.f-alpha)*scale};
}
inline std::array<float,3> drumFirstOrder(float frequency,bool highpass) noexcept {
    const float k=(frequency*6.2831854820251465f)*(1.f/48000.f),scale=1.f/(k+2.f),feedback=-(k-2.f)*scale;
    const float b0=highpass?scale+scale:k*scale,b1=highpass?-2.f*scale:k*scale;
    return {b0,b1,feedback};
}
}
