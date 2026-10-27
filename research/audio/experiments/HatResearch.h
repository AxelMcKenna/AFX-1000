#pragma once
#include "DrumResearchControls.h"
#include <array>
#include <span>
#include <cstddef>
#include <cstdint>
namespace rmx::research {
// Independently implemented neutral factory48k hi-hat research hypothesis.
class HatResearch {
public:
    void setControls(unsigned level,unsigned pitch) noexcept;
    void trigger() noexcept {if(processingStarted)requested=true;}
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
    uint32_t random1{0x77332244},random2{0xefcdab89};
    unsigned state{};bool requested{},processingStarted{};
};
}
