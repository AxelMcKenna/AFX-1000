#pragma once
#include <array>
#include <span>
#include <cstddef>
#include <cstdint>
namespace rmx::research {
// Independent research hypothesis, factory kick at stereo48k, neutral controls.
// Original scalar observations inform constants; complete waveform tests decide acceptance.
class KickResearch {
public:
    void trigger() noexcept {requested=true;}
    void process(std::span<float> output) noexcept;
private:
    struct Envelope {
        float attack{.001f},decay{},value{},position{};bool rising{},falling{};
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
    Envelope tone{.001f,.44f},pitch{.001f,.343f},noise{.001f,.15859f};
    Biquad bandpass,highpass{{.9981505274772644f,-1.9963010549545288f,.9981505274772644f,-1.9962975978851318f,.996304452419281f}};
    std::array<float,32> pending{};
    size_t received{},available{},head{};
    float phase1{.25f},phase2{.25f},gain{};
    uint32_t random1{0x1f9f4541},random2{0x93a6ff6c};
    unsigned state{};bool requested{};
};
}
