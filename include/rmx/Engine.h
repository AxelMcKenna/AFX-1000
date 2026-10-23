#pragma once
#include "AudioTypes.h"
#include "Parameters.h"
#include "TempoTracker.h"
#include "dsp/Isolator.h"
#include "dsp/ReleaseEffects.h"
#include "dsp/Sampler.h"
#include "dsp/SceneEffects.h"
#include "dsp/Sequencer.h"
#include "rmx/realtime/SpscQueue.h"
#include <span>
#include <type_traits>
namespace rmx {
// Diagnostics must remain lock-free inside the callback on a 32-bit audio MCU.
using EventCounter = std::conditional_t<std::atomic<uint64_t>::is_always_lock_free, uint64_t, uint32_t>;
static_assert(std::atomic<EventCounter>::is_always_lock_free);
struct MeterState {
    std::atomic<float> input{}, output{}, tempo{120}, confidence{}, load{};
    std::atomic<EventCounter> droppedEvents{};
};

class Engine {
  public:
    ParameterStore params;
    MeterState meters;
    void prepare(double sampleRate, uint32_t maxBlock);
    void reset() noexcept;
    // Install between callbacks or with processing stopped. The adapter retains
    // the bank until all callbacks using it have completed.
    void setBank(const SampleBank* bank) noexcept {
        setBank(SampleBankView(bank));
    }
    void setBank(SampleBankView bank) noexcept {
        sampler.setBank(bank);
    }
    bool enqueue(Event event) noexcept;
    // Planar stereo; input pointers may be null for sampler-only operation.
    // Sorted sample-offset events supplied directly by a host remain allocation-free.
    void process(const float* left, const float* right, float* outL, float* outR, uint32_t frames,
                 Transport transport = {}, std::span<const Event> events = {}) noexcept;
    double sampleRate() const noexcept {
        return sr;
    }

  private:
    dsp::Sampler sampler;
    dsp::Sequencer sequencer;
    dsp::Isolator isolator;
    dsp::SceneEffects sceneEffects;
    dsp::ReleaseEffects releaseEffects;
    SpscQueue<Event, 256> queue;
    std::array<float, parameterCount> p{}, smooth{};
    double sr{48000}, beat{}, bpm{120};
    uint64_t frame{}, lastTap{};
    float smoothing{}, bypassMix{}, sceneMix{};
    float isolateInputMix{1}, isolatePadMix{1}, sceneInputMix{1}, scenePadMix{1};
    TempoTracker tempoTracker;
    dsp::CachedValue<float> inputGain, outputGain;
    bool trackingTempo{};
    float get(Param x) const noexcept {
        return p[static_cast<size_t>(x)];
    }
    float sm(Param x) const noexcept {
        return smooth[static_cast<size_t>(x)];
    }
    dsp::Context context() const noexcept {
        return {p, smooth, sr, bpm, beat, frame, smoothing};
    }
    void event(Event e) noexcept;
    void resetEffects(bool panic) noexcept;
    void detectTempo(Stereo x) noexcept;
};
} // namespace rmx
