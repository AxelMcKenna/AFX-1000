#pragma once
#include "Dsp.h"
#include <array>
#include <cstdint>
#include <span>

namespace rmx {
// Factory Default Down, stereo 48 kHz. Other profiles/rates remain separate.
// Controls apply at callback boundaries; internally input and output advance
// independently in 32-frame blocks, including partial callbacks and startup.
class CalibratedReverbDown {
public:
    struct Controls {int main{128},amount{128},cutoff{};bool enabled{true};};
    static constexpr size_t maximumCallbackFrames=4096;
    void prepare(size_t maxFrames=maximumCallbackFrames);
    void reset() noexcept;
    // Audio-thread target update, before the following callback.
    void setControls(Controls controls) noexcept;
    // No allocation after prepare. In-place input/output is supported. An
    // optional dry trace must be separate from output. Invalid extents return
    // false without consuming audio or changing processor state. Non-finite
    // input is rejected under the same rule.
    bool process(std::span<const Stereo> input,std::span<Stereo> output,
                 std::span<Stereo> dry={}) noexcept;
    // Caller supplies the common 32-frame input/output clock. Generated sources
    // already carry their own master startup fade. Do not mix with process()
    // between resets; this entry point adds no second output FIFO.
    bool processGeneratedBlock(std::span<const Stereo,32> input,std::span<const Stereo,32> generated,
                               std::span<Stereo,32> output) noexcept;
    size_t storageBytes() const noexcept;
private:
    struct Delay {
        std::pmr::vector<double> data;size_t head{};
        void prepare(size_t maximum);
        void clear() noexcept;
        double tap(size_t delay) const noexcept;
        void push(double value) noexcept;
    };
    struct Filter {
        double b0{},b1{},b2{},a1{},a2{},s1{},s2{};
        void biquad(double hz,bool high) noexcept;
        void onePole(double hz,bool high) noexcept;
        void clear() noexcept;
        double tick(double x) noexcept;
    };
    struct AllPass {
        Delay delay;size_t length{};
        void prepare(size_t size);
        double tick(double x) noexcept;
    };
    struct Input {Stereo routed{};std::array<double,2> source{};bool selected{};};
    void initialize() noexcept;
    Input ingest(Stereo input) noexcept;
    void control(bool selected) noexcept;
    void configure(Controls controls) noexcept;
    std::array<Stereo,2> tick(Input input) noexcept;
    void setDry(float target,size_t length) noexcept;
    std::array<std::array<Delay,2>,5> combs;
    std::array<std::array<AllPass,2>,2> allpasses;
    std::array<std::array<Filter,2>,2> inputFilters;
    std::array<Filter,2> outputFilter,outputHigh;
    std::pmr::vector<Stereo> callbackInput;
    std::array<Input,32> collected{};
    std::array<Stereo,32> pending{},pendingDry{};
    size_t received{},available{},outputHead{};
    std::array<std::array<int,2>,5> delays{};
    std::array<std::array<float,2>,5> delayCurrent{},delayTarget{},delayStep{};
    std::array<double,12> coefficients{},targetCoefficients{},steps{};
    std::array<size_t,12> stagedRemaining{};
    Controls target{},state{};
    bool started{},prepared{},activationPrepared{},lastSelected{},everActivated{};
    bool geometryStart{},amountStart{};
    int slowMain{},pendingMain{},mainPeriod{60};
    size_t sharedBlocks{},geometryRemaining{},mixRemaining{};
    uint64_t frame{32},inputAge{},dryRestart{};
    double fastMix{},fastMixTarget{},fastMixStep{},dryGain{1},compensation{1};
    float startupFade{},inputFade{},dryCurrent{1},dryTarget{1},dryStep{};
    size_t warmRemaining{},dryRemaining{};
};
}
