#pragma once
#include <array>
#include <span>
#include <cstddef>
#include <cstdint>
namespace rmx::research {
// Factory48k snare hypothesis. Complete original renders decide fidelity.
class SnareResearch {
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
    struct FirstOrder {
        float b0{},b1{},feedback{},state{};
        float tick(float x) noexcept {const float y=b0*x+state;state=feedback*y+b1*x;return y;}
    };
    void block() noexcept;
    void start() noexcept;
    Envelope tone{.1875f},pitch{.035f},noise{.49f};
    Biquad bandpass,lowpass{{.21113240718841553f,.42226481437683105f,.21113240718841553f,-.523514986038208f,.3680446147918701f}};
    FirstOrder lowpass1{.370692640542984f,.370692640542984f,.25861474871635437f};
    FirstOrder highpass1{.6044127941131592f,-.6044127941131592f,.20882555842399597f};
    std::array<float,32> pending{};
    size_t received{},available{},head{};
    float phase1{.25f},phase2{.25f},gain{},startupGain{};
    float pitchRatio{1},outputLevel{1};
    uint32_t random1{0xd0f61b8f},random2{0x34373a95};
    unsigned state{};bool requested{},processingStarted{};
};
}
