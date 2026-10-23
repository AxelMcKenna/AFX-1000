#include "rmx/dsp/SceneEffects.h"
namespace rmx::dsp {
void SceneEffects::prepare(double sampleRate) {
    sceneDelay.prepare(static_cast<size_t>(sampleRate * 16) + 4);
    constexpr std::array<double, 8> seconds{.0297, .0371, .0411, .0437, .0531, .0613, .0719, .0797};
    for (size_t i = 0; i < 8; ++i)
        reverb[i].prepare(static_cast<size_t>(seconds[i] * sampleRate * 2) + 3);
    reset();
}
void SceneEffects::reset() noexcept {
    sceneDelay.clear();
    for (auto& delay : reverb)
        delay.clear();
    sceneFilter = {};
    feedbackFilter = {};
    reverbDamping = {};
    sceneRead = 0;
}
float SceneEffects::noise() noexcept {
    random ^= random << 13;
    random ^= random >> 17;
    random ^= random << 5;
    return static_cast<float>(static_cast<int32_t>(random)) / 2147483648.f;
}
Stereo SceneEffects::room(Stereo x, const Context& ctx) noexcept {
    constexpr std::array<double, 8> seconds{.0297, .0371, .0411, .0437, .0531, .0613, .0719, .0797};
    std::array<Stereo, 8> taps{};
    Stereo sum{}, wet{};
    const float size = .35f + ctx.get(Param::SceneTime) / 7 * 1.4f;
    const float decay =
        std::clamp(ctx.sm(Param::ReverbDecay) * .7f + ctx.sm(Param::SceneResonance) * .28f, .1f, .95f);
    for (size_t i = 0; i < 8; ++i) {
        taps[i] = reverbDamping[i].low(reverb[i].read(ctx.sr * seconds[i] * size),
                                       .12f + ctx.sm(Param::SceneResonance) * .3f);
        sum = sum + taps[i];
        wet = wet + taps[i] * (i % 2 ? .16f : -.16f);
    }
    for (size_t i = 0; i < 8; ++i)
        reverb[i].push(finite(x * .2f + (sum * .25f - taps[i]) * decay));
    return {wet.l + sum.r * .1f, wet.r + sum.l * .1f};
}
Stereo SceneEffects::process(Stereo x, float sceneMix, const Context& ctx) noexcept {
    const int type = static_cast<int>(ctx.get(Param::SceneType));
    const float depth = ctx.sm(Param::SceneDepth);
    const double delay =
        std::clamp(ctx.sr * 60 / ctx.bpm * beatDivisions[static_cast<size_t>(ctx.get(Param::SceneTime))], 2.,
                   ctx.sr * 14);
    Stereo echo = sceneDelay.read(delay), send = x, wet = echo;
    const float cutoff = 300 + depth * 10000;
    if (type == 0) {
        const Stereo lo = sceneFilter.low(x, coefficient(cutoff, ctx.sr));
        send = lo - feedbackFilter.low(lo, coefficient(cutoff * .35f, ctx.sr));
        wet = echo;
    }
    if (type == 2) {
        const float n = noise() * .35f;
        send = sceneFilter.low({n, n}, coefficient(300 + ctx.sm(Param::NoiseColor) * 12000, ctx.sr));
        wet = send + echo * .5f;
    }
    if (type == 3 || type == 8) {
        const double speed = std::pow(2., static_cast<double>(depth) * (type == 3 ? 1 : -1));
        sceneRead += 1 - speed;
        if (sceneRead < 0)
            sceneRead += delay;
        if (sceneRead >= delay)
            sceneRead -= delay;
        const double phase = sceneRead / delay;
        const float weight = static_cast<float>(.5 - .5 * std::cos(2 * pi * phase));
        wet = sceneDelay.read(2 + sceneRead) * weight +
              sceneDelay.read(2 + std::fmod(sceneRead + delay * .5, delay)) * (1 - weight);
    }
    if (type == 5)
        send = x - sceneFilter.low(x, coefficient(80 + depth * 7000, ctx.sr));
    if (type == 6)
        send = sceneFilter.low(x, coefficient(18000 * std::pow(.02f, depth), ctx.sr));
    if (type == 7) {
        const float steps = std::pow(2.f, 14 - depth * 11);
        send = {std::round(x.l * steps) / steps, std::round(x.r * steps) / steps};
        wet = echo + send * .3f;
    }
    if (type == 4 || type == 9)
        wet = room(type == 9 ? x * (1 - depth * .8f) : x, ctx);
    else
        (void)room({}, ctx); // Allow existing reverb to decay without stale frozen state.
    const float feedback =
        std::min(.96f, ctx.sm(Param::Feedback) * (.7f + ctx.sm(Param::SceneResonance) * .6f));
    sceneDelay.push(finite(send * sceneMix + echo * feedback));
    const float amount = depth * sceneMix;
    if (type == 2)
        return x + wet * amount;
    if (type >= 5)
        return mix(x, send * (1 - depth * .7f) + wet * depth, sceneMix * depth);
    return x + wet * (amount * .8f);
}
} // namespace rmx::dsp
