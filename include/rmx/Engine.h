#pragma once
#include "Parameters.h"
#include "TempoTracker.h"
#include <array>
#include <atomic>
#include <span>
#include <vector>

namespace rmx {
struct Stereo { float l{}, r{}; };
inline Stereo operator+(Stereo a,Stereo b) { return {a.l+b.l,a.r+b.r}; }
inline Stereo operator-(Stereo a,Stereo b) { return {a.l-b.l,a.r-b.r}; }
inline Stereo operator*(Stereo a,float s) { return {a.l*s,a.r*s}; }
inline Stereo mix(Stereo a,Stereo b,float t) { return a*(1-t)+b*t; }
struct Sample { std::vector<Stereo> frames; double rate{48000}; };
struct SampleBank { std::array<Sample,16> slots; };
SampleBank makeFactoryBank(double rate=48000);

enum class EventType : uint8_t { Trigger, RollStart, RollStop, Tap, ClearSequence, Panic };
struct Event { EventType type{}; uint8_t pad{}; float velocity{1}; uint32_t offset{}; };
struct Transport { double bpm{120}; double beat{}; bool synced{}, playing{true}; };
struct MeterState { std::atomic<float> input{}, output{}, tempo{120}, confidence{}, load{}; std::atomic<uint64_t> droppedEvents{}; };

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
    // Planar stereo; input pointers may be null for sampler-only operation.
    // Sorted sample-offset events supplied directly by a host remain allocation-free.
    void process(const float* left,const float* right,float* outL,float* outR,uint32_t frames,
                 Transport transport={},std::span<const Event> events={}) noexcept;
    double sampleRate() const noexcept { return sr; }
private:
    class Delay {
    public:
        void prepare(size_t n) { buffer.assign(n,{}); head=0; }
        void clear() noexcept { std::fill(buffer.begin(),buffer.end(),Stereo{}); head=0; }
        Stereo read(double ago) const noexcept;
        void push(Stereo v) noexcept { buffer[head]=v; head=(head+1)%buffer.size(); }
    private: std::vector<Stereo> buffer; size_t head{};
    } sceneDelay, history, rollHistory;
    struct BandLoop { Delay history; std::vector<Stereo> frozen; size_t length{},copied{}; uint64_t start{}; double position{}; bool active{}; };
    std::array<std::array<BandLoop,3>,2> bandLoops;
    std::vector<Stereo> capturedRoll; size_t capturedLength{},captureCopied{}; double capturePosition{}; uint64_t captureFrame{};
    struct Filter { Stereo z{}; Stereo low(Stereo in,float a) noexcept { z=z+(in-z)*a; return z; } } sceneFilter, feedbackFilter;
    std::array<Filter,2> lowSplit,highSplit;
    struct Voice { int slot{-1}; double position{}; float velocity{}; uint32_t age{}; };
    struct Pending { uint64_t at{}; uint8_t pad{}; float velocity{}; bool record{}; };
    struct Step { uint8_t pad{}; float velocity{}; uint16_t tick{}; bool active{}; };
    std::array<Voice,32> voices{};
    std::array<Pending,64> pending{}; size_t pendingCount{};
    std::array<Step,128> sequence{}; size_t sequenceSize{};
    std::array<Delay,8> reverb;
    std::array<Filter,8> reverbDamping;
    SpscQueue<Event,256> queue;
    const SampleBank* samples{};
    std::array<float,parameterCount> p{}, smooth{};
    double sr{48000}, beat{}, bpm{120}, rollNext{}, rollStart{}, sceneRead{}, releaseRead{}, releaseAge{};
    uint64_t frame{},lastTap{};
    int rollPad{-1}, selectedPad{}, lastTick{-1};
    bool previousRelease{}, previousOverdub{}, sourceRoll{};
    float smoothing{},lowAlpha{},highAlpha{},bypassMix{},sceneMix{},releaseMix{};
    float isolateInputMix{1},isolatePadMix{1},sceneInputMix{1},scenePadMix{1};
    uint32_t random{0x12345678};
    TempoTracker tempoTracker;
    float get(Param x) const noexcept { return p[static_cast<size_t>(x)]; }
    float sm(Param x) const noexcept { return smooth[static_cast<size_t>(x)]; }
    float noise() noexcept;
    void event(Event e) noexcept;
    void trigger(int pad,float velocity) noexcept;
    void schedule(int pad,float velocity) noexcept;
    Stereo sample() noexcept;
    Stereo isolate(Stereo x,size_t bus) noexcept;
    Stereo scene(Stereo x) noexcept;
    Stereo room(Stereo x) noexcept;
    Stereo release(Stereo x) noexcept;
    void detectTempo(Stereo x) noexcept;
};
}
