#pragma once
#include "Dsp.h"
#include <array>
#include <memory_resource>
#include <vector>
#include <cstdint>

namespace rmx {
struct SceneSettings {
    int type{};
    std::array<int,10> sub2Mode{},waveform{},resonance{},width{1,1,1,1,1,1,1,1,1,1},feedbackCharacter{1,1,1,1,1,1,1,1,1,1};
    int echoFilter{},echoFeedbackMode{1},noiseMinimum{},noiseMaximum{};
    std::array<int,2> spiralPitchMode{},spiralTimeSpan{1,1},roomSize{},reverbTime{1,1};
    std::array<int,2> reverbFilter{2,0};
    std::array<std::array<int,4>,10> delayBeats=[] {
        std::array<std::array<int,4>,10> choices{};
        for(auto& regions:choices)regions={1,2,3,5};
        return choices;
    }();
    float feedback{.55f},decay{.72f},noiseColor{.5f};
    bool operator==(const SceneSettings&) const=default;
};
class SceneProcessor {
public:
    void prepare(double sampleRate);
    void reset() noexcept;
    void configure(const SceneSettings&) noexcept;
    Stereo process(Stereo input,float macro,float sub1,float sub2,float enabled,double bpm,double beat,float sidechain) noexcept;
private:
    FractionalDelay echo,spiral;
    std::array<FractionalDelay,8> room;
    std::array<Stereo,8> damping{};
    StateFilter mainFilter,echoFilter,noiseTilt;
    SceneSettings settings;
    double rate{48000},pitchPhase{};uint64_t frame{};
    uint32_t random{0x12345678};
    float previousCutoff{-1},previousQ{-1},previousEchoCutoff{-1},dampingAlpha{},sidechainEnvelope{};
    std::array<std::array<double,8>,2> roomLengths{};
    std::array<std::array<float,8>,2> roomGains{};
    unsigned roomSide{};float sideAttack{},sideRelease{};
    void updateRoom() noexcept;
    float noise() noexcept;
    float modulation(float amount,double beat) const noexcept;
    Stereo reverb(Stereo input) noexcept;
};
}
