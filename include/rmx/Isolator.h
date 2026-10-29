#pragma once
#include "Dsp.h"
#include <array>
#include <cstdint>
#include <memory_resource>
#include <vector>

namespace rmx {
struct IsolatorSettings {
    int mode{};
    // Fitted to the factory isolator's measured 48 kHz transfer functions.
    float lowHz{283.99944f},highHz{4649.0398f};
    std::array<int,3> minimum{3,3,3},maximum{2,2,2};
    std::array<int,3> addPattern{},transPattern{},rollPattern{},gateDepth{1,1,1},driveDepth{1,1,1};
    int kickStrength{1}; bool cutHpfResonance{},cutLpfResonance{};
    bool operator==(const IsolatorSettings&) const=default;
};
class Isolator {
public:
    void prepare(double sampleRate);
    void reset() noexcept;
    std::array<std::span<Stereo>,6> loanableStorage() noexcept;
    void setStorageLoaned(bool loaned) noexcept;
    void configure(const IsolatorSettings& settings) noexcept;
    void tempo(double bpm) noexcept { secondsPerBeat=60/std::clamp(bpm,40.,240.); }
    Stereo process(Stereo input,const std::array<float,3>& controls,double beat) noexcept;
private:
    struct Band {
        FractionalDelay history; std::pmr::vector<Stereo> capture;
        size_t captured{},length{}; double position{}; bool recording{};
        float envelope{},gate{1},transGain{1};
    };
    std::array<Band,3> bands;
    StateFilter kickFilter,cutHighPass,cutLowPass;
    std::array<StateFilter,3> lowCrossover;
    std::array<StateFilter,4> highCrossover;
    Stereo lowState{},highState{};
    IsolatorSettings settings;
    double secondsPerBeat{.5},rate{48000}; uint64_t frame{};
    float lowAlpha{},highAlpha{},attack{},release{},gateAttack{},gateRelease{},transSlew{},kickSlowAlpha{},kickDecay{};
    float kickFast{},kickSlow{},kickGate{}; unsigned kickRefractory{};
    float lastMid{2},lastHigh{2}; bool configured{},storageLoaned{};
    Stereo cut(Stereo input,const std::array<float,3>& controls) noexcept;
    Stereo roll(Band& band,Stereo input,float control,size_t length) noexcept;
};
}
