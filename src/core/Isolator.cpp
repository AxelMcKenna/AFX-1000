#include "rmx/dsp/Isolator.h"
namespace rmx::dsp {
void Isolator::prepare(double sampleRate) {
    for (auto& bus : bandLoops)
        for (auto& band : bus) {
            band.history.prepare(static_cast<size_t>(sampleRate) + 4);
            band.frozen.assign(static_cast<size_t>(sampleRate) + 4, {});
        }
    reset();
}
void Isolator::reset() noexcept {
    for (auto& bus : bandLoops)
        for (auto& band : bus) {
            band.history.clear();
            band.active = false;
            band.copied = 0;
            band.position = 0;
            band.length = 0;
        }
    lowSplit = {};
    highSplit = {};
    lowCoefficient = {};
    highCoefficient = {};
    driveNormalization = {};
    hasSignal = {};
}
void Isolator::configure(float lowHz, float highHz, double sampleRate) noexcept {
    lowAlpha = lowCoefficient.get(lowHz, [&](float hz) { return coefficient(hz, sampleRate); });
    highAlpha = highCoefficient.get(highHz, [&](float hz) { return coefficient(hz, sampleRate); });
}
Stereo Isolator::process(Stereo x, size_t bus, const Context& ctx) noexcept {
    // An untouched, silent bus has no filter or capture history to maintain.
    // Once used, keep its histories running so a later roll captures prehistory.
    if (!hasSignal[bus]) {
        const bool freezing =
            static_cast<int>(ctx.get(Param::IsolateMode)) == 2 &&
            (ctx.sm(Param::Low) > .0001f || ctx.sm(Param::Mid) > .0001f || ctx.sm(Param::High) > .0001f);
        if (level(x) == 0 && !freezing)
            return {};
        hasSignal[bus] = true;
    }
    Stereo low = lowSplit[bus].low(x, lowAlpha), upper = highSplit[bus].low(x, highAlpha);
    std::array<Stereo, 3> bands{low, upper - low, x - upper};
    const int mode = static_cast<int>(ctx.get(Param::IsolateMode));
    const float gate = mode == 1 || mode == 2 ? static_cast<float>(std::fmod(ctx.beat * 4, 1.) < .5) : 0.f;
    Stereo out{};
    for (size_t b = 0; b < 3; ++b) {
        const float k = ctx.sm(static_cast<Param>(static_cast<int>(Param::Low) + b));
        Stereo y = bands[b];
        auto& loop = bandLoops[bus][b];
        loop.history.push(y);
        if (mode != 2 || k <= .0001f)
            loop.active = false;
        if (mode == 0)
            y = y * (k < 0 ? 1 + k : 1 + k * 2);
        else if (mode == 1) {
            y = k < 0 ? y * (1 + k) : y * (1 + k * gate * 2);
        } else if (mode == 2) {
            if (k < 0)
                y = y * (1 + k * (1 - gate));
            else if (k > .0001f) {
                constexpr std::array<double, 5> subdivisions{1, 2, 4, 8, 16};
                const auto length = std::max(
                    size_t(8), static_cast<size_t>(60 * ctx.sr / ctx.bpm * .25 /
                                                   subdivisions[static_cast<size_t>(std::floor(k * 4))]));
                if (!loop.active || loop.length != length) {
                    loop.active = true;
                    loop.length = std::min(length, loop.frozen.size());
                    loop.copied = 0;
                    loop.position = 0;
                    loop.start = ctx.frame;
                }
                for (int n = 0; n < 4 && loop.copied < loop.length; ++n, ++loop.copied)
                    loop.frozen[loop.copied] = loop.history.read(
                        static_cast<double>(ctx.frame - loop.start + loop.length - loop.copied));
                const auto index = static_cast<size_t>(loop.position);
                auto read = [&](size_t i) {
                    return i < loop.copied ? loop.frozen[i]
                                           : loop.history.read(static_cast<double>(ctx.frame - loop.start +
                                                                                   loop.length - i));
                };
                const float fade = std::min(1.f, static_cast<float>(index) / 16) *
                                   std::min(1.f, static_cast<float>(loop.length - index) / 16);
                y = mix(y, read(index) * fade, k);
                loop.position += 1;
                if (loop.position >= loop.length)
                    loop.position = 0;
            }
        } else {
            const float magnitude = level(y);
            if (k < 0) {
                const float threshold = -k * .2f;
                y = y * std::clamp((magnitude - threshold) * 50.f, 0.f, 1.f);
            } else if (k > 1.e-5f) {
                const float drive = 1 + k * 12;
                const float normalization =
                    driveNormalization[b].get(drive, [](float d) { return std::sqrt(d); });
                y = {std::tanh(y.l * drive) / normalization, std::tanh(y.r * drive) / normalization};
            }
        }
        out = out + y;
    }
    return out;
}
} // namespace rmx::dsp
