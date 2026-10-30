#pragma once
#include "rmx/drums/Controls.h"
#include <array>
#include <span>
#include <cstddef>
#include <cstdint>
namespace rmx::drums {
// Independently implemented neutral factory48k hi-hat research hypothesis.
class Hat {
public:
    void setProfile(unsigned gain,unsigned decay,bool envelope) noexcept;
    void setControls(unsigned level,unsigned pitch) noexcept;
    void trigger(float velocity=1) noexcept {if(processingStarted){requested=true;requestedVelocity=std::clamp(velocity,0.f,1.f);}}
    void stop() noexcept {state=0;requested=false;pending.fill(0);}
    void reset() noexcept {*this={};}
    void process(std::span<float> output) noexcept;
    // Shared-clock adapter: use after reset, without mixing with process().
    void beginProcessing() noexcept {processingStarted=true;}
    void generateBlock(std::span<float,32> output) noexcept {block();std::copy(pending.begin(),pending.end(),output.begin());}
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
    void block() noexcept;
    void start() noexcept;
    Envelope main{.3f},attack{.3f*.7875f};
    Biquad highpass1{{.8089153170585632f,-1.6178306341171265f,.8089153170585632f,-1.5370112657546997f,.698650062084198f}};
    Biquad highpass2{{.5809150338172913f,-1.1618300676345825f,.5809150338172913f,-.9315155148506165f,.3921445310115814f}};
    std::array<float,32> pending{};
    std::array<float,4> phase{};
    size_t received{},available{},head{};
    float gain{},startupGain{},pitchRatio{1};
    DrumLevelRamp outputLevel;
    float customizationGain{1};bool linearEnvelope{};
    float voiceVelocity{1},nextVelocity{1},requestedVelocity{1};
    uint32_t random1{0x77332244},random2{0xefcdab89};
    unsigned state{};bool requested{},processingStarted{};
};
}
