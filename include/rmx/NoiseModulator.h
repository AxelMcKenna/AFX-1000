#pragma once
#include <algorithm>
#include <array>
#include <cstdint>

namespace rmx {
// Reconstructed control trajectories. Random uses the project's own generator.
// No manufacturer audio, executable code or random-generator state is stored.
class NoiseModulator {
public:
    void reset() noexcept { *this=NoiseModulator{}; }
    const std::array<float,32>& sidechain(int raw,const std::array<float,32>& detector,float target) noexcept;
    const std::array<float,32>& generate(int raw,int wave,bool resonance=false) noexcept;
private:
    std::array<float,32> output{};
    float phase{},period{9600},depth{},randomTarget{},randomStep{};
    float threshold{.05f},thresholdTarget{.05f},thresholdStep{},envelope{},gate{1};
    unsigned thresholdBlocks{};
    uint32_t counter{},random{0x6b8b4567};
    int smoothed{};
    unsigned remaining{};
    bool initialized{},descending{};
};
}
