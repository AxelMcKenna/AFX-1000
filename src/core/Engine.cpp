#include "rmx/Engine.h"

namespace rmx {
using dsp::coefficient;
using dsp::db;
using dsp::finite;
using dsp::level;
void Engine::prepare(double sampleRate, uint32_t maxBlock) {
    (void)maxBlock;
    sr = std::clamp(sampleRate, 8000., 192000.);
    sampler.prepare(sr);
    isolator.prepare(sr);
    sceneEffects.prepare(sr);
    releaseEffects.prepare(sr);
    smoothing = 1 - std::exp(-1.f / static_cast<float>(sr * .008));
    tempoTracker.prepare(sr);
    reset();
}
void Engine::reset() noexcept {
    sampler.reset();
    sequencer.reset();
    isolator.reset();
    sceneEffects.reset();
    releaseEffects.reset();
    frame = 0;
    beat = 0;
    bpm = params.get(Param::Tempo);
    lastTap = 0;
    bypassMix = params.get(Param::Bypass);
    sceneMix = 0;
    p = params.snapshot();
    smooth = p;
    isolateInputMix = (get(Param::IsolateSource) == 0 || get(Param::IsolateSource) == 2) ? 1.f : 0.f;
    isolatePadMix = (get(Param::IsolateSource) == 1 || get(Param::IsolateSource) == 2) ? 1.f : 0.f;
    sceneInputMix = (get(Param::SceneSource) == 0 || get(Param::SceneSource) == 2) ? 1.f : 0.f;
    scenePadMix = (get(Param::SceneSource) == 1 || get(Param::SceneSource) == 2) ? 1.f : 0.f;
    tempoTracker.reset();
    trackingTempo = false;
    inputGain = {};
    outputGain = {};
    Event e;
    while (queue.pop(e)) {
    }
}
bool Engine::enqueue(Event e) noexcept {
    if (queue.push(e))
        return true;
    meters.droppedEvents.fetch_add(1, std::memory_order_relaxed);
    return false;
}
void Engine::resetEffects(bool panic) noexcept {
    for (auto p : {Param::SceneOn, Param::Low, Param::Mid, Param::High, Param::XHold, Param::Overdub})
        params.set(p, 0);
    if (panic)
        params.set(Param::ReleaseAmount, 0);
    p = params.snapshot();
    sampler.stop();
    sequencer.reset();
}
void Engine::event(Event e) noexcept {
    switch (e.type) {
    case EventType::Trigger:
        if (!sequencer.schedule(e.pad, e.velocity, context()))
            meters.droppedEvents.fetch_add(1, std::memory_order_relaxed);
        break;
    case EventType::RollStart:
        sequencer.startRoll(e.pad, beat);
        break;
    case EventType::RollStop:
        if (get(Param::XHold) < .5f) {
            sequencer.stopRoll();
            sampler.stopRoll();
        }
        break;
    case EventType::ClearSequence:
        sequencer.clear();
        break;
    case EventType::Panic:
        resetEffects(true);
        break;
    case EventType::Tap:
        if (lastTap > 0) {
            const double tapped = 60 * sr / (frame - lastTap);
            if (tapped >= 40 && tapped <= 240) {
                params.set(Param::Tempo, static_cast<float>(tapped));
                params.set(Param::AutoTempo, 0);
                bpm = tapped;
            }
        }
        lastTap = frame ? frame : 1;
        beat = std::floor(beat);
        break;
    }
}
void Engine::detectTempo(Stereo x) noexcept {
    tempoTracker.process(x.l, x.r);
    if (frame % 256 == 0) {
        meters.confidence.store(tempoTracker.certainty(), std::memory_order_relaxed);
        if (get(Param::AutoTempo) > .5f && tempoTracker.certainty() > .15f)
            bpm = tempoTracker.bpm();
    }
}
void Engine::process(const float* left, const float* right, float* outL, float* outR, uint32_t frames,
                     Transport transport, std::span<const Event> events) noexcept {
    if (!frames)
        return;
    p = params.snapshot();
    if (get(Param::UserSettings) < .5f)
        for (auto setting : {Param::LowCrossover, Param::HighCrossover, Param::Feedback, Param::ReverbDecay,
                             Param::NoiseColor, Param::Swing})
            p[static_cast<size_t>(setting)] = parameters[static_cast<size_t>(setting)].initial;
    if (transport.synced && std::isfinite(transport.bpm) && transport.bpm >= 40 && transport.bpm <= 240) {
        bpm = transport.bpm;
        if (std::isfinite(transport.beat))
            beat = transport.beat;
    } else if (get(Param::AutoTempo) < .5f)
        bpm = get(Param::Tempo);
    isolator.configure(get(Param::LowCrossover), get(Param::HighCrossover), sr);
    Event e;
    for (unsigned count = 0; count < 255 && queue.pop(e); ++count)
        event(e);
    const bool trackTempo = !transport.synced && get(Param::AutoTempo) > .5f;
    if (trackTempo != trackingTempo) {
        tempoTracker.reset();
        meters.confidence.store(0, std::memory_order_relaxed);
        trackingTempo = trackTempo;
    }
    size_t eventIndex = 0;
    float inputPeak = 0, outputPeak = 0;
    for (uint32_t i = 0; i < frames; ++i, ++frame) {
        while (eventIndex < events.size() && events[eventIndex].offset <= i)
            event(events[eventIndex++]);
        // Only values consumed through sm() need interpolation. Discrete choices
        // and block settings never use these smoothed copies.
        for (auto parameter :
             {Param::InputGain, Param::OutputGain, Param::SceneDepth, Param::SceneResonance, Param::Low,
              Param::Mid, Param::High, Param::XLevel, Param::XPitch, Param::ReleaseAmount, Param::Feedback,
              Param::ReverbDecay, Param::NoiseColor, Param::SamplerMute}) {
            const auto k = static_cast<size_t>(parameter);
            smooth[k] += (p[k] - smooth[k]) * smoothing;
        }
        sequencer.process(context(), transport.playing,
                          [&](int pad, float velocity) { sampler.trigger(pad, velocity, context()); });
        Stereo raw{left ? left[i] : 0, right ? right[i] : (left ? left[i] : 0)};
        raw = finite(raw);
        const float gain = inputGain.get(sm(Param::InputGain), db);
        Stereo input = raw * gain;
        inputPeak = std::max(inputPeak, level(input));
        if (trackTempo)
            detectTempo(input);
        sampler.capture(input);
        Stereo drums = sampler.process(context(), sequencer.rolling()), processed{};
        const int isoSource = static_cast<int>(get(Param::IsolateSource));
        isolateInputMix += (((isoSource == 0 || isoSource == 2) ? 1.f : 0.f) - isolateInputMix) * smoothing;
        isolatePadMix += (((isoSource == 1 || isoSource == 2) ? 1.f : 0.f) - isolatePadMix) * smoothing;
        input = mix(input, isolator.process(input, 0, context()), isolateInputMix);
        drums = mix(drums, isolator.process(drums, 1, context()), isolatePadMix);
        const int sceneSource = static_cast<int>(get(Param::SceneSource));
        sceneInputMix += (((sceneSource == 0 || sceneSource == 2) ? 1.f : 0.f) - sceneInputMix) * smoothing;
        scenePadMix += (((sceneSource == 1 || sceneSource == 2) ? 1.f : 0.f) - scenePadMix) * smoothing;
        sceneMix += (get(Param::SceneOn) * std::max(sceneInputMix, scenePadMix) - sceneMix) * smoothing;
        const Stereo send = input * sceneInputMix + drums * scenePadMix;
        processed = input + drums + (sceneEffects.process(send, sceneMix, context()) - send);
        if (releaseEffects.justReleased(get(Param::ReleaseAmount)))
            resetEffects(false);
        processed = releaseEffects.process(processed, context());
        if (get(Param::WetOnly) > .5f)
            processed = processed - raw * gain;
        processed = processed * outputGain.get(sm(Param::OutputGain), db);
        bypassMix += (get(Param::Bypass) - bypassMix) * smoothing;
        processed = finite(mix(processed, raw, bypassMix));
        // Transparent below unity; bounded soft protection above unity.
        auto protect = [](float v) {
            const float a = std::abs(v);
            return a <= 1 ? v : std::copysign(1 + .25f * std::tanh((a - 1) * 4), v);
        };
        outL[i] = protect(processed.l);
        outR[i] = protect(processed.r);
        outputPeak = std::max(outputPeak, level({outL[i], outR[i]}));
        if (transport.playing)
            beat += bpm / (60 * sr);
    }
    meters.input.store(inputPeak, std::memory_order_relaxed);
    meters.output.store(outputPeak, std::memory_order_relaxed);
    meters.tempo.store(static_cast<float>(bpm), std::memory_order_relaxed);
}
} // namespace rmx
