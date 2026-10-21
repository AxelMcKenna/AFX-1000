#pragma once
#include <array>
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <string_view>

namespace rmx {
enum class Param : uint16_t {
    InputGain, OutputGain, Bypass, WetOnly, Tempo, Quantize, AutoTempo,
    SceneType, SceneOn, SceneDepth, SceneTime, SceneResonance, SceneSource,
    IsolateMode, Low, Mid, High, IsolateSource,
    XLevel, XPitch, XRoll, XHold, XSource, Bank, Overdub,
    ReleaseType, ReleaseAmount, ReleaseTime,
    LowCrossover, HighCrossover, Feedback, ReverbDecay, NoiseColor,
    Swing,SamplerMute,UserSettings,Count
};
inline constexpr size_t parameterCount = static_cast<size_t>(Param::Count);
struct ParameterInfo { std::string_view id, name; float min, max, initial; bool discrete; };
inline constexpr std::array<ParameterInfo, parameterCount> parameters {{
    {"input_gain", "Input gain", -24, 12, 0, false},
    {"output_gain", "Output gain", -24, 12, 0, false},
    {"bypass", "Bypass", 0, 1, 0, true},
    {"wet_only", "Send/return", 0, 1, 0, true},
    {"tempo", "BPM", 40, 240, 120, false},
    {"quantize", "Quantize", 0, 1, 1, true},
    {"auto_tempo", "Auto BPM", 0, 1, 0, true},
    {"scene_type", "Scene FX", 0, 9, 0, true},
    {"scene_on", "Scene enabled", 0, 1, 0, true},
    {"scene_depth", "Scene depth", 0, 1, 0.35f, false},
    {"scene_time", "Scene beat", 0, 7, 3, true},
    {"scene_resonance", "Resonance", 0, 1, 0.3f, false},
    {"scene_source", "Scene source", 0, 3, 2, true},
    {"isolate_mode", "Isolator mode", 0, 3, 0, true},
    {"low", "Low", -1, 1, 0, false},
    {"mid", "Mid", -1, 1, 0, false},
    {"high", "High", -1, 1, 0, false},
    {"isolate_source", "Isolator source", 0, 3, 2, true},
    {"x_level", "Sampler level", 0, 1.5f, 0.75f, false},
    {"x_pitch", "Sampler pitch", -24, 24, 0, false},
    {"x_roll", "Roll beat", 0, 7, 3, true},
    {"x_hold", "Roll hold", 0, 1, 0, true},
    {"x_source", "X-Pad source", 0, 1, 0, true},
    {"bank", "Sample bank", 0, 3, 0, true},
    {"overdub", "Overdub", 0, 1, 0, true},
    {"release_type", "Release FX", 0, 2, 0, true},
    {"release_amount", "Release lever", 0, 1, 0, false},
    {"release_time", "Release time", 0.125f, 4, 1, false},
    {"low_crossover", "Low crossover", 80, 500, 250, false},
    {"high_crossover", "High crossover", 1000, 10000, 4000, false},
    {"feedback", "Delay feedback", 0, 0.94f, 0.55f, false},
    {"reverb_decay", "Reverb decay", 0.1f, 0.95f, 0.72f, false},
    {"noise_color", "Noise color", 0, 1, 0.5f, false},
    {"swing", "Swing", 0, 0.45f, 0, false},
    {"sampler_mute", "Sampler mute", 0, 1, 0, true},
    {"user_settings", "Default / User settings", 0, 1, 0, true}
}};
inline constexpr std::array<std::string_view, 10> sceneNames {"BPF Echo", "Echo", "Noise", "Spiral Up", "Reverb Up", "HPF Echo", "LPF Echo", "Crush Echo", "Spiral Down", "Reverb Down"};
inline constexpr std::array<std::string_view, 4> isolateNames {"Isolate", "Cut / Add", "Trans / Roll", "Gate / Drive"};
inline constexpr std::array<std::string_view, 3> releaseNames {"Back Spin", "Echo", "Vinyl Brake"};
inline constexpr std::array<std::string_view, 4> drumNames {"Kick", "Snare", "Clap", "Hi-Hat"};
inline constexpr std::array<float, 8> beatDivisions {0.0625f, 0.125f, 0.25f, 0.5f, 0.75f, 1, 2, 4};
inline constexpr std::array<std::string_view, 8> beatNames {"1/16", "1/8", "1/4", "1/2", "3/4", "1", "2", "4"};
inline float sanitize(Param p, float value) noexcept {
    const auto& info = parameters[static_cast<size_t>(p)];
    if (!std::isfinite(value)) value = info.initial;
    value = std::clamp(value, info.min, info.max);
    return info.discrete ? std::round(value) : value;
}
class ParameterStore {
public:
    ParameterStore() { for (size_t i=0; i<parameterCount; ++i) values[i].store(parameters[i].initial); }
    float get(Param p) const noexcept { return values[static_cast<size_t>(p)].load(std::memory_order_relaxed); }
    void set(Param p, float v) noexcept { values[static_cast<size_t>(p)].store(sanitize(p,v), std::memory_order_relaxed); }
    std::array<float, parameterCount> snapshot() const noexcept {
        std::array<float, parameterCount> s{};
        for(size_t i=0;i<parameterCount;++i) s[i]=values[i].load(std::memory_order_relaxed);
        return s;
    }
private:
    std::array<std::atomic<float>, parameterCount> values;
};
}
