#include "rmx/dsp/Sampler.h"
namespace rmx::dsp {
void Sampler::prepare(double sampleRate) {
    rollHistory.prepare(static_cast<size_t>(sampleRate * 16) + 4);
    capturedRoll.assign(static_cast<size_t>(sampleRate * 8) + 4, {});
    reset();
}
void Sampler::reset() noexcept {
    stop();
    rollHistory.clear();
    capturedLength = 0;
    captureCopied = 0;
    capturePosition = 0;
    captureFrame = 0;
    pitchRatio = {};
}
void Sampler::trigger(int pad, float velocity, const Context& ctx) noexcept {
    if (ctx.get(Param::XSource) > .5f) {
        capturedLength =
            std::min(capturedRoll.size(),
                     static_cast<size_t>(ctx.sr * 60 / ctx.bpm *
                                         beatDivisions[static_cast<size_t>(ctx.get(Param::XRoll))]));
        captureCopied = 0;
        captureFrame = ctx.frame;
        capturePosition = 0;
        sourceRoll = true;
        return;
    }
    Voice* voice = &voices[0];
    for (auto& v : voices) {
        if (v.slot < 0) {
            voice = &v;
            break;
        }
        if (v.age > voice->age)
            voice = &v;
    }
    *voice = {static_cast<int>(ctx.get(Param::Bank)) * 4 + pad % 4, 0, std::clamp(velocity, 0.f, 1.f), 0};
}
Stereo Sampler::process(const Context& ctx, bool rolling) noexcept {
    Stereo out{};
    const double ratio =
        pitchRatio.get(ctx.sm(Param::XPitch), [](double pitch) { return std::pow(2., pitch / 12.); });
    for (auto& v : voices) {
        if (v.slot < 0)
            continue;
        const auto* sample = samples.slots[static_cast<size_t>(v.slot)];
        if (!sample) {
            v.slot = -1;
            continue;
        }
        const auto& asset = *sample;
        const auto index = static_cast<size_t>(v.position);
        if (index + 1 >= asset.frames.size()) {
            v.slot = -1;
            continue;
        }
        const float fade = std::min(1.f, static_cast<float>(v.age) / 32.f) *
                           std::min(1.f, static_cast<float>(asset.frames.size() - index) / 64.f);
        out =
            out + mix(asset.frames[index], asset.frames[index + 1], static_cast<float>(v.position - index)) *
                      (v.velocity * fade);
        v.position += ratio * asset.rate / ctx.sr;
        ++v.age;
    }
    if (sourceRoll && capturedLength > 1) {
        // Copy the frozen window incrementally: never copy seconds of audio in one callback.
        for (int copied = 0; copied < 32 && captureCopied < capturedLength; ++copied, ++captureCopied)
            capturedRoll[captureCopied] = rollHistory.read(
                static_cast<double>(ctx.frame - captureFrame + capturedLength - captureCopied));
        const auto i = static_cast<size_t>(capturePosition) % capturedLength;
        const float fade = std::min(1.f, static_cast<float>(i) / 32.f) *
                           std::min(1.f, static_cast<float>(capturedLength - i) / 32.f);
        auto captured = [&](size_t index) {
            return index < captureCopied ? capturedRoll[index]
                                         : rollHistory.read(static_cast<double>(ctx.frame - captureFrame +
                                                                                capturedLength - index));
        };
        out = out + mix(captured(i), captured((i + 1) % capturedLength),
                        static_cast<float>(capturePosition - std::floor(capturePosition))) *
                        fade;
        capturePosition += ratio;
        if (capturePosition >= capturedLength) {
            capturePosition = std::fmod(capturePosition, static_cast<double>(capturedLength));
            if (!rolling)
                sourceRoll = false;
        }
    }
    return out * (ctx.sm(Param::XLevel) * (1 - ctx.sm(Param::SamplerMute)));
}
} // namespace rmx::dsp
