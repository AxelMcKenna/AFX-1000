#pragma once
#include <algorithm>
#include <array>
#include <cstdint>

namespace rmx {
// Reconstructed control trajectories and Random modulation initialization.
// No manufacturer audio, executable code or captured PRNG memory is stored.
class NoiseModulator {
public:
    struct RandomSource {
        float (*next)(void*) noexcept;
        void* state;
    };
    void reset() noexcept { *this=NoiseModulator{}; }
    const std::array<float,32>& sidechain(int raw,const std::array<float,32>& detector,float target) noexcept;
    const std::array<float,32>& generate(int raw,int wave,bool resonance=false,const RandomSource* source=nullptr) noexcept;
    uint32_t randomDrawCount() const noexcept { return randomDraws; }
    float randomTargetValue() const noexcept { return randomTarget; }
private:
    std::array<float,32> output{};
    float phase{},period{9600},depth{},randomTarget{},randomStep{},randomPhase{};
    float threshold{.05f},thresholdTarget{.05f},thresholdStep{},envelope{},gate{1};
    unsigned thresholdBlocks{};
    uint32_t counter{},randomFirst{1193046},randomSecond{16702650};
    uint32_t randomDraws{};
    int smoothed{};
    unsigned remaining{};
    bool initialized{},descending{};
};
}
