#pragma once
#include "Primitives.h"
namespace rmx::dsp {
class SceneEffects {
  public:
    void prepare(double sampleRate);
    void reset() noexcept;
    Stereo process(Stereo x, float sceneMix, const Context& ctx) noexcept;

  private:
    Delay sceneDelay;
    Filter sceneFilter, feedbackFilter;
    std::array<Delay, 8> reverb;
    std::array<Filter, 8> reverbDamping;
    double sceneRead{};
    uint32_t random{0x12345678};
    CachedValue<float> bandCoefficient, feedbackCoefficient, noiseCoefficient;
    CachedValue<float> highpassCoefficient, lowpassCoefficient, crushSteps;
    CachedValue<double> spiralSpeed;
    size_t quietReverbFrames{}, quietInputFrames{}, reverbBufferFrames{};
    bool reverbActive{};
    float noise() noexcept;
    Stereo room(Stereo x, const Context& ctx) noexcept;
};
} // namespace rmx::dsp
