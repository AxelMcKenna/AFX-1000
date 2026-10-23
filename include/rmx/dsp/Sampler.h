#pragma once
#include "Primitives.h"
namespace rmx::dsp {
class Sampler {
  public:
    void prepare(double sampleRate);
    void reset() noexcept;
    void stop() noexcept {
        voices = {};
        sourceRoll = false;
    }
    void stopRoll() noexcept {
        sourceRoll = false;
    }
    void setBank(SampleBankView bank) noexcept {
        samples = bank;
    }
    void capture(Stereo input) noexcept {
        rollHistory.push(input);
    }
    void trigger(int pad, float velocity, const Context& ctx) noexcept;
    Stereo process(const Context& ctx, bool rolling) noexcept;

  private:
    struct Voice {
        int slot{-1};
        double position{};
        float velocity{};
        uint32_t age{};
    };
    std::array<Voice, 32> voices{};
    SampleBankView samples;
    Delay rollHistory;
    std::vector<Stereo> capturedRoll;
    size_t capturedLength{}, captureCopied{};
    double capturePosition{};
    uint64_t captureFrame{};
    bool sourceRoll{};
    CachedValue<double> pitchRatio;
};
} // namespace rmx::dsp
