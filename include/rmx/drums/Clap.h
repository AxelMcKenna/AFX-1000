#pragma once
#include "rmx/drums/Controls.h"
#include <array>
#include <span>
#include <cstddef>
#include <cstdint>
namespace rmx::drums {
// Independently implemented neutral factory48k clap research hypothesis.
class Clap {
public:
    void setControls(unsigned level,unsigned pitch) noexcept;
    void trigger(float velocity=1) noexcept {if(processingStarted){requested=true;requestedVelocity=std::clamp(velocity,0.f,1.f);}}
    void stop() noexcept {state=0;requested=false;pending.fill(0);}
    void reset() noexcept {*this={};}
    void process(std::span<float> output) noexcept;
private:
    struct Envelope {
        float decay{},value{},position{};bool rising{},falling{};
        void start() noexcept {value=position=0;rising=true;falling=false;}
        float advance() noexcept;
    };
    struct Biquad {
        std::array<float,5> coefficients{};double s1{},s2{};
        float tick(float x) noexcept;
        void clear() noexcept {s1=s2=0;}
    };
    struct FirstOrder {
        float b0{},b1{},feedback{},state{};
        float tick(float x) noexcept {const float y=b0*x+state;state=feedback*y+b1*x;return y;}
    };
    void block() noexcept;
    void start() noexcept;
    Envelope noise{.24f},tail{1.25f};
    Biquad bandpass{{.07508103549480438f,0,-.07508103549480438f,-1.8378087282180786f,.8498378992080688f}};
    Biquad highpass{{.9279578924179077f,-1.8559157848358154f,.9279578924179077f,-1.850794792175293f,.8610365390777588f}};
    FirstOrder lowpass1{.049754731357097626f,.049754731357097626f,.9004905819892883f};
    std::array<float,32> pending{};
    size_t received{},available{},head{};
    float phase{1},gain{},startupGain{};
    DrumLevelRamp outputLevel;
    float voiceVelocity{1},nextVelocity{1},requestedVelocity{1};
    uint32_t random1{0xb741fe44},random2{0x2c342f89};
    unsigned state{},elapsed{};bool requested{},processingStarted{};
};
}
