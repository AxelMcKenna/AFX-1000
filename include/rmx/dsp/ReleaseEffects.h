#pragma once
#include "Primitives.h"
namespace rmx::dsp {
class ReleaseEffects {
  public:
    void prepare(double sampleRate) {
        history.prepare(static_cast<size_t>(sampleRate * 16) + 4);
        reset();
    }
    void reset() noexcept {
        history.clear();
        previousRelease = false;
        releaseRead = 0;
        releaseAge = 0;
        releaseMix = 0;
    }
    bool justReleased(float amount) const noexcept {
        return amount <= .005f && previousRelease;
    }
    Stereo process(Stereo x, const Context& ctx) noexcept;

  private:
    Delay history;
    double releaseRead{}, releaseAge{};
    float releaseMix{};
    bool previousRelease{};
};
} // namespace rmx::dsp
