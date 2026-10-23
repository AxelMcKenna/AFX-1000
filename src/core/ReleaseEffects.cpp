#include "rmx/dsp/ReleaseEffects.h"
namespace rmx::dsp {
Stereo ReleaseEffects::process(Stereo x, const Context& ctx) noexcept {
    const bool active = ctx.get(Param::ReleaseAmount) > .005f;
    if (active && !previousRelease) {
        releaseAge = 0;
        releaseRead = 0;
    }
    previousRelease = active;
    releaseMix += (static_cast<float>(active) - releaseMix) * ctx.smoothing;
    Stereo wet{};
    if (active || releaseMix > .0001f) {
        const float lever = ctx.sm(Param::ReleaseAmount);
        const double duration =
            std::max(.05, static_cast<double>(ctx.get(Param::ReleaseTime)) * 60 / ctx.bpm) *
            (2.5 - 1.5 * lever) * ctx.sr;
        const int type = static_cast<int>(ctx.get(Param::ReleaseType));
        if (type == 0) {
            releaseRead += 1 + lever * 3 * std::exp(-releaseAge / duration);
            wet = history.read(releaseAge + releaseRead + 1) *
                  static_cast<float>(std::exp(-releaseAge / (duration * 2)));
        } else if (type == 1) {
            const double length = std::min(ctx.sr * 8., ctx.sr * 60 / ctx.bpm *
                                                            (lever < .5    ? 1.
                                                             : lever < .85 ? .5
                                                                           : .25));
            wet = history.read(releaseAge + length - std::fmod(releaseAge, length)) *
                  static_cast<float>(std::pow(.35 + .3 * lever, releaseAge / length));
        } else {
            const double speed = std::max(0., 1 - releaseAge / duration);
            releaseRead += speed;
            wet = history.read(releaseAge - releaseRead + 2) * static_cast<float>(speed);
        }
        ++releaseAge;
    }
    history.push(x);
    return mix(x, wet, releaseMix);
}
} // namespace rmx::dsp
