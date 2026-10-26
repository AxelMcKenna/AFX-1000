#pragma once
#include "Parameters.h"
#include "TempoTracker.h"
#include "Sequencer.h"
#include "Dsp.h"
#include "Isolator.h"
#include "Scene.h"
#include "Sample.h"
#include "LoopStretch.h"
#include "CalibratedReverbDown.h"
#include <array>
#include <atomic>
#include <span>
#include <vector>
#include <memory_resource>

namespace rmx {
static_assert(std::atomic<float>::is_always_lock_free && std::atomic<uint32_t>::is_always_lock_free,
              "Audio parameters and counters require lock-free 32-bit atomics");
SampleBank makeFactoryBank(double rate=48000,bool fillSampleBanks=true);

enum class EventType : uint8_t { Trigger, RollStart, RollStop, Tap, ClearSequence, Panic, MutePad, DeletePad, Nudge, NudgeStart, NudgeStop,SelectPad };
struct Event { EventType type{}; uint8_t pad{}; float velocity{1}; uint32_t offset{};uint8_t bank{255},source{255}; };
struct Transport { double bpm{120}; double beat{}; bool synced{}, playing{true}; };
struct MeterState { std::atomic<float> input{}, output{}, tempo{120}, confidence{}, load{},protectionGain{1}; std::atomic<uint32_t> droppedEvents{}; std::atomic<unsigned> sequenceSteps{}, padMuteMask{}; };

// One producer (UI or the adapter's merged event source), one audio consumer.
template<class T, size_t Capacity> class SpscQueue {
    static_assert((Capacity & (Capacity-1)) == 0);
public:
    bool push(const T& v) noexcept {
        const auto w=write.load(std::memory_order_relaxed), n=(w+1)&(Capacity-1);
        if(n==read.load(std::memory_order_acquire)) return false;
        data[w]=v; write.store(n,std::memory_order_release); return true;
    }
    bool pop(T& v) noexcept {
        const auto r=read.load(std::memory_order_relaxed);
        if(r==write.load(std::memory_order_acquire)) return false;
        v=data[r]; read.store((r+1)&(Capacity-1),std::memory_order_release); return true;
    }
private:
    std::array<T,Capacity> data{};
    alignas(64) std::atomic<size_t> write{};
    alignas(64) std::atomic<size_t> read{};
};

class Engine {
public:
    ParameterStore params;
    MeterState meters;
    void prepare(double sampleRate, uint32_t maxBlock);
    void reset() noexcept;
    // Call with processing stopped; assets remain adapter-owned for the engine lifetime.
    void setBank(const SampleBank* bank) noexcept { samples=bank; }
    bool enqueue(Event event) noexcept;
    Event captureEvent(Event event) const noexcept;
    // Planar stereo; input pointers may be null for sampler-only operation.
    // Sorted sample-offset events supplied directly by a host remain allocation-free.
    void process(const float* left,const float* right,float* outL,float* outR,uint32_t frames,
                 Transport transport={},std::span<const Event> events={}) noexcept;
    double sampleRate() const noexcept { return sr; }
    // Nominal processing delay for the selected profile, including button-off.
    // The measured Down callback adapter also reproduces partial-block startup.
    unsigned latencySamples() const noexcept;
private:
    FractionalDelay history;
    SceneProcessor sceneProcessor;
    CalibratedReverbDown reverbDown;
    struct ReleaseFrame {
        double bpm{};float amount{},time{},mix{};int type{};bool active{},start{};
    };
    struct OutputFrame {ReleaseFrame release;float gain{},bypass{};bool wetOnly{},downEnabled{};};
    struct ParallelAudio {Stereo raw{},unselected{},wetDry{};};
    std::pmr::vector<Stereo> sceneInput,sceneOutput,downOutput;
    std::pmr::vector<OutputFrame> outputFrames;
    std::pmr::vector<ParallelAudio> parallelInput,parallelOutput;
    std::array<ParallelAudio,32> routingCollected{},routingPending{};
    size_t routingReceived{},routingAvailable{},routingHead{};
    uint64_t routingAge{};float routingFade{};
    void alignDownAudio(size_t start,size_t count) noexcept;
    Stereo rollInput{};
    std::array<Isolator,2> isolators;
    std::pmr::vector<Stereo> capturedRoll; size_t capturedLength{},captureCopied{}; double capturePosition{};
    struct Voice { int slot{-1}; double position{}; float velocity{}; uint32_t age{}; LoopStretch stretch; float envelope{1},envelopeStep{1},punch{},punchStep{}; };
    std::array<Voice,32> voices{};
    Sequencer sequence;
    SpscQueue<Event,256> queue;
    const SampleBank* samples{};
    std::array<float,parameterCount> p{}, smooth{};
    double sr{48000}, beat{}, bpm{120}, rollNext{}, rollStart{}, releaseRead{}, releaseAge{};
    uint64_t frame{},lastTap{};
    int rollPad{-1}, selectedPad{}, nudgeDirection{};
    double nudgeOffset{},autoPhaseSlew{};
    std::array<double,4> tapIntervals{}; size_t tapCount{},tapIndex{}; bool tapped{};
    bool previousRelease{}, previousOverdub{}, sourceRoll{},wasExternalSync{};
    float smoothing{},bypassMix{},sceneMix{},releaseMix{},rollInputMix{};
    float protectionGain{1},protectionRelease{};
    float isolateInputMix{1},isolatePadMix{1},sceneInputMix{1},scenePadMix{1};
    TempoTracker tempoTracker;
    float get(Param x) const noexcept { return p[static_cast<size_t>(x)]; }
    float sm(Param x) const noexcept { return smooth[static_cast<size_t>(x)]; }
    void event(Event e) noexcept;
    bool trigger(int pad,float velocity,int bank=-1,int source=-1,bool toggleLoop=false) noexcept;
    void stopSample(int pad,int bank,int source) noexcept;
    void hit(int pad,float velocity,int bank=-1,int source=-1,bool toggleLoop=true) noexcept;
    void set(Param parameter,float value) noexcept;
    Stereo sample() noexcept;
    Stereo isolate(Stereo x,size_t bus) noexcept;
    Stereo scene(Stereo x) noexcept;
    ReleaseFrame releaseControls() noexcept;
    Stereo release(Stereo x,const ReleaseFrame&) noexcept;
    void detectTempo(Stereo x) noexcept;
};
}
