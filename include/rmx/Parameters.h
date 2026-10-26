#pragma once
#include <array>
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <string_view>
#include <span>

namespace rmx {
enum class Param : uint16_t {
    InputGain, OutputGain, Bypass, WetOnly, Tempo, Quantize, AutoTempo,
    SceneType, SceneOn, SceneDepth, SceneTime, SceneResonance, SceneSource,
    IsolateMode, Low, Mid, High, IsolateSource,
    XLevel, XPitch, XRoll, XHold, XSource, Bank, Overdub,
    ReleaseType, ReleaseAmount, ReleaseTime,
    LowCrossover, HighCrossover, Feedback, ReverbDecay, NoiseColor,
    Swing,SamplerMute,UserSettings,ReleaseKeepScene,ReleaseKeepIsolate,ReleaseKeepSampler,IsolateMinLow,IsolateMinMid,IsolateMinHigh,IsolateMaxLow,IsolateMaxMid,IsolateMaxHigh,CutKickStrength,CutHpfResonance,CutLpfResonance,AddPatternLow,AddPatternMid,AddPatternHigh,TransPatternLow,TransPatternMid,TransPatternHigh,BandRollPatternLow,BandRollPatternMid,BandRollPatternHigh,GateDepthLow,GateDepthMid,GateDepthHigh,DriveDepthLow,DriveDepthMid,DriveDepthHigh,BpfModMode,BpfWave,BpfResonance,BpfFeedbackChar,HpfModMode,HpfWave,HpfResonance,HpfFeedbackChar,LpfModMode,LpfWave,LpfResonance,LpfFeedbackChar,BpfWidth,CrushWave,CrushWidth,CrushFeedbackChar,NoiseModMode,NoiseWave,NoiseResonance,NoiseWidth,NoiseMinimum,NoiseMaximum,EchoFilter,EchoFeedbackMode,EchoFeedbackChar,SpiralUpPitchMode,SpiralUpTimeSpan,SpiralUpFeedbackChar,SpiralDownPitchMode,SpiralDownTimeSpan,SpiralDownFeedbackChar,ReverbUpRoomSize,ReverbUpTime,ReverbDownRoomSize,ReverbDownTime,
    BpfDelay1, BpfDelay2, BpfDelay3, BpfDelay4, EchoDelay1, EchoDelay2, EchoDelay3, EchoDelay4, SpiralUpDelay1, SpiralUpDelay2, SpiralUpDelay3, SpiralUpDelay4, HpfDelay1, HpfDelay2, HpfDelay3, HpfDelay4, LpfDelay1, LpfDelay2, LpfDelay3, LpfDelay4, CrushDelay1, CrushDelay2, CrushDelay3, CrushDelay4, SpiralDownDelay1, SpiralDownDelay2, SpiralDownDelay3, SpiralDownDelay4, EchoWidth, ReverbUpFilter, ReverbDownFilter, SampleSource,
    XPadBeat1, XPadBeat2, XPadBeat3, XPadBeat4, XPadBeat5, XPadBeat6, XPadBeat7, XPadBeat8, KickGain, SnareGain, ClapGain, HatGain, KickDecay, SnareDecay, ClapDecay, HatDecay, KickEnvelope, SnareEnvelope, ClapEnvelope, HatEnvelope, PitchDownRange, PitchUpRange,
    IsolateOn, Count // Append new host parameters to preserve existing indices.
};
inline constexpr size_t parameterCount = static_cast<size_t>(Param::Count);
struct ParameterInfo { std::string_view id, name; float min, max, initial; bool discrete; bool advanced{}; };
inline constexpr std::array<ParameterInfo, parameterCount> parameters {{
    {"input_gain", "Input gain", -24, 12, 0, false},
    {"output_gain", "Output gain", -24, 12, 0, false},
    {"bypass", "Bypass", 0, 1, 0, true},
    {"wet_only", "Send/return", 0, 1, 0, true},
    {"tempo", "BPM", 40, 240, 120, false},
    {"quantize", "Quantize", 0, 1, 1, true},
    {"auto_tempo", "Auto BPM", 0, 1, 1, true},
    {"scene_type", "Scene FX", 0, 9, 0, true},
    {"scene_on", "Scene enabled", 0, 1, 0, true},
    {"scene_depth", "Scene depth", 0, 1, 0, false},
    {"scene_time", "Scene sub parameter 1", 0, 7, 128*7.f/255, false},
    {"scene_resonance", "Scene sub parameter 2", 0, 1, 0, false},
    {"scene_source", "Scene source", 0, 3, 2, true},
    {"isolate_mode", "Isolator mode", 0, 3, 0, true},
    {"low", "Low", -1, 1, 0, false},
    {"mid", "Mid", -1, 1, 0, false},
    {"high", "High", -1, 1, 0, false},
    {"isolate_source", "Isolator source", 0, 3, 2, true},
    {"x_level", "Sampler level", 0, 1.5f, 0.75f, false},
    {"x_pitch", "Sampler pitch travel", -24, 24, 0, false},
    {"x_roll", "X-Pad position", 0, 7, 3, true},
    {"x_hold", "Roll hold", 0, 1, 0, true},
    {"x_source", "X-Pad source", 0, 1, 0, true},
    {"bank", "Sample bank", 0, 3, 0, true},
    {"overdub", "Overdub", 0, 1, 0, true},
    {"release_type", "Release FX", 0, 2, 1, true},
    {"release_amount", "Release lever", 0, 1, 0, false},
    {"release_time", "Release time", 0.125f, 4, 1, false, true},
    {"low_crossover", "Low crossover", 80, 500, 283.99944f, false, true},
    {"high_crossover", "High crossover", 1000, 10000, 4649.0398f, false, true},
    {"feedback", "Delay feedback", 0, 0.94f, 0.7f, false, true},
    {"reverb_decay", "Reverb decay", 0.1f, 0.95f, 0.72f, false, true},
    {"noise_color", "Noise color", 0, 1, 0.5f, false, true},
    {"swing", "Swing", 0, 0.45f, 0, false, true},
    {"sampler_mute", "Sampler mute", 0, 1, 0, true},
    {"user_settings", "Default / User settings", 0, 1, 0, true},
    {"release_keep_scene", "Release retains Scene FX", 0, 1, 0, true, true},
    {"release_keep_isolate", "Release retains Isolate FX", 0, 1, 0, true, true},
    {"release_keep_sampler", "Release retains X-Pad FX", 0, 1, 0, true, true},
    {"isolate_min_low", "Low isolator minimum", 0, 3, 3, true, true},
    {"isolate_min_mid", "Mid isolator minimum", 0, 3, 3, true, true},
    {"isolate_min_high", "High isolator minimum", 0, 3, 3, true, true},
    {"isolate_max_low", "Low isolator maximum", 0, 3, 2, true, true},
    {"isolate_max_mid", "Mid isolator maximum", 0, 3, 2, true, true},
    {"isolate_max_high", "High isolator maximum", 0, 3, 2, true, true},
    {"cut_kick_strength", "Cut kick reduction", 0, 2, 1, true, true},
    {"cut_hpf_resonance", "Cut high-pass resonance", 0, 1, 0, true, true},
    {"cut_lpf_resonance", "Cut low-pass resonance", 0, 1, 0, true, true},
    {"add_pattern_low", "Low add delay pattern", 0, 2, 0, true, true},
    {"add_pattern_mid", "Mid add delay pattern", 0, 2, 0, true, true},
    {"add_pattern_high", "High add delay pattern", 0, 2, 0, true, true},
    {"trans_pattern_low", "Low trans rhythm pattern", 0, 2, 0, true, true},
    {"trans_pattern_mid", "Mid trans rhythm pattern", 0, 2, 0, true, true},
    {"trans_pattern_high", "High trans rhythm pattern", 0, 2, 0, true, true},
    {"band_roll_pattern_low", "Low band roll beat pattern", 0, 2, 0, true, true},
    {"band_roll_pattern_mid", "Mid band roll beat pattern", 0, 2, 0, true, true},
    {"band_roll_pattern_high", "High band roll beat pattern", 0, 2, 0, true, true},
    {"gate_depth_low", "Low gate depth", 0, 2, 1, true, true},
    {"gate_depth_mid", "Mid gate depth", 0, 2, 1, true, true},
    {"gate_depth_high", "High gate depth", 0, 2, 1, true, true},
    {"drive_depth_low", "Low drive depth", 0, 2, 1, true, true},
    {"drive_depth_mid", "Mid drive depth", 0, 2, 1, true, true},
    {"drive_depth_high", "High drive depth", 0, 2, 1, true, true},
    {"bpf_sub2_mode", "BPF Echo Sub2 mode", 0, 1, 0, true, true},
    {"bpf_wave", "BPF Echo modulation wave", 0, 4, 0, true, true},
    {"bpf_resonance", "BPF Echo resonance character", 0, 2, 0, true, true},
    {"bpf_feedback_character", "BPF Echo feedback character", 0, 2, 1, true, true},
    {"hpf_sub2_mode", "HPF Echo Sub2 mode", 0, 1, 0, true, true},
    {"hpf_wave", "HPF Echo modulation wave", 0, 4, 0, true, true},
    {"hpf_resonance", "HPF Echo resonance character", 0, 2, 0, true, true},
    {"hpf_feedback_character", "HPF Echo feedback character", 0, 2, 1, true, true},
    {"lpf_sub2_mode", "LPF Echo Sub2 mode", 0, 1, 0, true, true},
    {"lpf_wave", "LPF Echo modulation wave", 0, 4, 0, true, true},
    {"lpf_resonance", "LPF Echo resonance character", 0, 2, 0, true, true},
    {"lpf_feedback_character", "LPF Echo feedback character", 0, 2, 1, true, true},
    {"bpf_width", "BPF Echo pass width", 0, 2, 1, true, true},
    {"crush_wave", "Crush Echo modulation wave", 0, 4, 0, true, true},
    {"crush_width", "Crush Echo filter width", 0, 2, 1, true, true},
    {"crush_feedback_character", "Crush Echo feedback character", 0, 2, 1, true, true},
    {"noise_sub2_mode", "Noise Sub2 mode", 0, 1, 0, true, true},
    {"noise_wave", "Noise modulation wave", 0, 4, 0, true, true},
    {"noise_resonance", "Noise resonance character", 0, 2, 0, true, true},
    {"noise_width", "Noise filter width", 0, 2, 1, true, true},
    {"noise_minimum", "Noise minimum level", 0, 3, 1, true, true},
    {"noise_maximum", "Noise maximum level", 0, 3, 2, true, true},
    {"echo_filter", "Echo filter type", 0, 2, 2, true, true},
    {"echo_feedback_mode", "Echo feedback mode", 0, 1, 1, true, true},
    {"echo_feedback_character", "Echo feedback character", 0, 2, 1, true, true},
    {"spiral_up_pitch_mode", "Spiral Up pitch variation", 0, 1, 0, true, true},
    {"spiral_up_time_span", "Spiral Up delay time span", 0, 2, 1, true, true},
    {"spiral_up_feedback_character", "Spiral Up feedback character", 0, 2, 1, true, true},
    {"spiral_down_pitch_mode", "Spiral Down pitch variation", 0, 1, 0, true, true},
    {"spiral_down_time_span", "Spiral Down delay time span", 0, 2, 1, true, true},
    {"spiral_down_feedback_character", "Spiral Down feedback character", 0, 2, 1, true, true},
    {"reverb_up_room_size", "Reverb Up room size", 0, 1, 0, true, true},
    {"reverb_up_time", "Reverb Up decay time", 0, 2, 1, true, true},
    {"reverb_down_room_size", "Reverb Down room size", 0, 1, 0, true, true},
    {"reverb_down_time", "Reverb Down decay time", 0, 2, 1, true, true},
    {"bpf_delay_1", "BPF Echo delay region 1", 0, 6, 2, true, true},
    {"bpf_delay_2", "BPF Echo delay region 2", 0, 6, 3, true, true},
    {"bpf_delay_3", "BPF Echo delay region 3", 0, 6, 4, true, true},
    {"bpf_delay_4", "BPF Echo delay region 4", 0, 6, 5, true, true},
    {"echo_delay_1", "Echo delay region 1", 0, 8, 2, true, true},
    {"echo_delay_2", "Echo delay region 2", 0, 8, 3, true, true},
    {"echo_delay_3", "Echo delay region 3", 0, 8, 4, true, true},
    {"echo_delay_4", "Echo delay region 4", 0, 8, 5, true, true},
    {"spiral_up_delay_1", "Spiral Up delay region 1", 0, 6, 1, true, true},
    {"spiral_up_delay_2", "Spiral Up delay region 2", 0, 6, 2, true, true},
    {"spiral_up_delay_3", "Spiral Up delay region 3", 0, 6, 3, true, true},
    {"spiral_up_delay_4", "Spiral Up delay region 4", 0, 6, 5, true, true},
    {"hpf_delay_1", "HPF Echo delay region 1", 0, 6, 2, true, true},
    {"hpf_delay_2", "HPF Echo delay region 2", 0, 6, 3, true, true},
    {"hpf_delay_3", "HPF Echo delay region 3", 0, 6, 4, true, true},
    {"hpf_delay_4", "HPF Echo delay region 4", 0, 6, 5, true, true},
    {"lpf_delay_1", "LPF Echo delay region 1", 0, 6, 2, true, true},
    {"lpf_delay_2", "LPF Echo delay region 2", 0, 6, 3, true, true},
    {"lpf_delay_3", "LPF Echo delay region 3", 0, 6, 4, true, true},
    {"lpf_delay_4", "LPF Echo delay region 4", 0, 6, 5, true, true},
    {"crush_delay_1", "Crush Echo delay region 1", 0, 6, 2, true, true},
    {"crush_delay_2", "Crush Echo delay region 2", 0, 6, 3, true, true},
    {"crush_delay_3", "Crush Echo delay region 3", 0, 6, 4, true, true},
    {"crush_delay_4", "Crush Echo delay region 4", 0, 6, 5, true, true},
    {"spiral_down_delay_1", "Spiral Down delay region 1", 0, 6, 1, true, true},
    {"spiral_down_delay_2", "Spiral Down delay region 2", 0, 6, 2, true, true},
    {"spiral_down_delay_3", "Spiral Down delay region 3", 0, 6, 3, true, true},
    {"spiral_down_delay_4", "Spiral Down delay region 4", 0, 6, 5, true, true},
    {"echo_width", "Echo filter width", 0, 2, 1, true, true},
    {"reverb_up_filter", "Reverb Up filter type", 0, 2, 2, true, true},
    {"reverb_down_filter", "Reverb Down filter type", 0, 2, 0, true, true},
    {"sample_source", "Sample source", 0, 1, 0, true},
    {"x_pad_beat_1", "X-Pad position 1 beat", 0, 15, 2, true, true},
    {"x_pad_beat_2", "X-Pad position 2 beat", 0, 15, 4, true, true},
    {"x_pad_beat_3", "X-Pad position 3 beat", 0, 15, 6, true, true},
    {"x_pad_beat_4", "X-Pad position 4 beat", 0, 15, 8, true, true},
    {"x_pad_beat_5", "X-Pad position 5 beat", 0, 15, 10, true, true},
    {"x_pad_beat_6", "X-Pad position 6 beat", 0, 15, 11, true, true},
    {"x_pad_beat_7", "X-Pad position 7 beat", 0, 15, 13, true, true},
    {"x_pad_beat_8", "X-Pad position 8 beat", 0, 15, 14, true, true},
    {"kick_gain", "Kick gain", -3, 3, 0, true, true},
    {"snare_gain", "Snare gain", -3, 3, 0, true, true},
    {"clap_gain", "Clap gain", -3, 3, 0, true, true},
    {"hat_gain", "Hi-hat gain", -3, 3, 0, true, true},
    {"kick_decay", "Kick decay", 0, 2, 1, true, true},
    {"snare_decay", "Snare decay", 0, 2, 1, true, true},
    {"clap_decay", "Clap decay", 0, 2, 1, true, true},
    {"hat_decay", "Hi-hat decay", 0, 2, 1, true, true},
    {"kick_envelope", "Kick envelope", 0, 1, 0, true, true},
    {"snare_envelope", "Snare envelope", 0, 1, 0, true, true},
    {"clap_envelope", "Clap envelope", 0, 1, 0, true, true},
    {"hat_envelope", "Hi-hat envelope", 0, 1, 0, true, true},
    {"pitch_down_range", "Pitch down range (semitones)", 1, 24, 24, true, true},
    {"pitch_up_range", "Pitch up range (semitones)", 1, 24, 24, true, true},
    {"isolate_on", "Isolate enabled", 0, 1, 0, true}
}};
inline constexpr std::array<std::string_view, 10> sceneNames {"BPF Echo", "Echo", "Noise", "Spiral Up", "Reverb Up", "HPF Echo", "LPF Echo", "Crush Echo", "Spiral Down", "Reverb Down"};
inline constexpr std::array<std::string_view, 4> isolateNames {"Isolate", "Cut / Add", "Trans / Roll", "Gate / Drive"};
inline constexpr std::array<std::string_view, 3> releaseNames {"Back Spin", "Echo", "Vinyl Brake"};
inline constexpr std::array<std::string_view, 4> drumNames {"Kick", "Snare", "Clap", "Hi-Hat"};
inline constexpr std::array<double,16> xPadBeatValues{1./32,1./24,1./16,1./12,1./8,1./6,1./4,1./3,1./2,2./3,3./4,1,3./2,2,4,8};
inline constexpr std::array<std::string_view,16> xPadBeatNames{"1/32","1/24","1/16","1/12","1/8","1/6","1/4","1/3","1/2","2/3","3/4","1/1","3/2","2/1","4/1","8/1"};
inline constexpr std::array<std::string_view,8> xPadPositionNames{"Position 1","Position 2","Position 3","Position 4","Position 5","Position 6","Position 7","Position 8"};
// Scene FX has four independently assignable Sub1 regions. X-Pad divisions
// retain their separate parameter domain.
inline constexpr std::array<double,9> sceneDelayBeats{.0625,.125,.25,.5,.75,1,2,4,8};
inline constexpr std::array<std::string_view,9> sceneDelayNames{"1/16","1/8","1/4","1/2","3/4","1/1","2/1","4/1","8/1"};
struct SceneDelayGroup { int scene;Param first; };
inline constexpr std::array<SceneDelayGroup,7> sceneDelayGroups{{
    {0,Param::BpfDelay1},
    {1,Param::EchoDelay1},
    {3,Param::SpiralUpDelay1},
    {5,Param::HpfDelay1},
    {6,Param::LpfDelay1},
    {7,Param::CrushDelay1},
    {8,Param::SpiralDownDelay1}
}};
inline size_t sceneDelayRegion(float sub1) noexcept {
    if(!std::isfinite(sub1))return 0;
    return std::min(size_t{3},static_cast<size_t>(static_cast<double>(std::clamp(sub1,0.f,7.f))*(4./7)));
}
inline size_t echoDelayRegion(float sub1) noexcept {
    if(!std::isfinite(sub1))return 0;
    const auto raw=std::clamp(static_cast<int>(std::floor(std::clamp(sub1,0.f,7.f)*(255.f/7)+1.e-4f)),0,255);
    // Independent static factory captures locate these three transitions.
    return raw<66?0:raw<132?1:raw<194?2:3;
}
inline constexpr std::array<std::string_view,4> isolatorMinNames{"-6 dB","-12 dB","-18 dB","Full kill"};
inline constexpr std::array<std::string_view,4> isolatorMaxNames{"0 dB","+3 dB","+6 dB","+9 dB"};
inline constexpr std::array<std::string_view,3> patternNames{"Pattern 1","Pattern 2","Pattern 3"};
inline constexpr std::array<std::string_view,3> strengthNames{"Mild","Default","Wild"};
inline constexpr std::array<std::string_view,2> switchNames{"Off","On"};
inline constexpr std::array<std::string_view,2> modModeNames{"Modulation","Resonance"},feedbackModeNames{"Hold","DJM"},pitchModeNames{"Linear","Key"},roomNames{"Large","Small"};
inline constexpr std::array<std::string_view,3> resonanceNames{"Default","Mild","None"},widthNames{"Narrow","Normal","Wide"},filterNames{"Low-pass","Band-pass","High-pass"},timeNames{"Short","Default","Long"};
inline constexpr std::array<std::string_view,2> envelopeNames{"Type 1","Type 2"};
inline constexpr std::array<std::string_view,5> waveNames{"Triangle","Saw","Square","Random","Side-chain"};
inline constexpr std::array<std::string_view,4> noiseMinNames{"Off","-18 dB","-12 dB","-6 dB"};
inline constexpr std::array<std::string_view,2> settingNames{"Default","User"},sampleSourceNames{"Samples","Input Roll"};
inline constexpr std::array<std::string_view,4> sourceNames{"Input","X-Pad","Both","Neither"},bankNames{"Bank 1","Bank 2","Bank 3","Bank 4"};
inline constexpr std::array<std::string_view,2> drumSourceNames{"Internal drums","Bank samples"};
inline std::span<const std::string_view> parameterChoices(Param p) noexcept {
    if(p>=Param::KickDecay&&p<=Param::HatDecay)return timeNames;
    if(p>=Param::KickEnvelope&&p<=Param::HatEnvelope)return envelopeNames;
    if(p==Param::UserSettings)return settingNames;
    if(p==Param::SceneType)return sceneNames;
    if(p==Param::IsolateMode)return isolateNames;
    if(p==Param::ReleaseType)return releaseNames;
    if(p==Param::SceneSource||p==Param::IsolateSource)return sourceNames;
    if(p==Param::Bank)return bankNames;
    if(p==Param::SampleSource)return drumSourceNames;
    if(p==Param::XSource)return sampleSourceNames;
    if(p==Param::XRoll)return xPadPositionNames;
    if(p>=Param::XPadBeat1&&p<=Param::XPadBeat8)return xPadBeatNames;
    if(p>=Param::BpfDelay1&&p<=Param::SpiralDownDelay4) return std::span(sceneDelayNames).first(parameters[static_cast<size_t>(p)].max==8?9:7);
    if(p==Param::EchoWidth)return widthNames;
    if(p==Param::ReverbUpFilter||p==Param::ReverbDownFilter)return filterNames;
    switch(p) {
        case Param::BpfModMode:return modModeNames;
        case Param::BpfWave:return waveNames;
        case Param::BpfResonance:return resonanceNames;
        case Param::BpfFeedbackChar:return strengthNames;
        case Param::HpfModMode:return modModeNames;
        case Param::HpfWave:return waveNames;
        case Param::HpfResonance:return resonanceNames;
        case Param::HpfFeedbackChar:return strengthNames;
        case Param::LpfModMode:return modModeNames;
        case Param::LpfWave:return waveNames;
        case Param::LpfResonance:return resonanceNames;
        case Param::LpfFeedbackChar:return strengthNames;
        case Param::BpfWidth:return widthNames;
        case Param::CrushWave:return waveNames;
        case Param::CrushWidth:return widthNames;
        case Param::CrushFeedbackChar:return strengthNames;
        case Param::NoiseModMode:return modModeNames;
        case Param::NoiseWave:return waveNames;
        case Param::NoiseResonance:return resonanceNames;
        case Param::NoiseWidth:return strengthNames;
        case Param::NoiseMinimum:return noiseMinNames;
        case Param::NoiseMaximum:return isolatorMaxNames;
        case Param::EchoFilter:return filterNames;
        case Param::EchoFeedbackMode:return feedbackModeNames;
        case Param::EchoFeedbackChar:return strengthNames;
        case Param::SpiralUpPitchMode:return pitchModeNames;
        case Param::SpiralUpTimeSpan:return strengthNames;
        case Param::SpiralUpFeedbackChar:return strengthNames;
        case Param::SpiralDownPitchMode:return pitchModeNames;
        case Param::SpiralDownTimeSpan:return strengthNames;
        case Param::SpiralDownFeedbackChar:return strengthNames;
        case Param::ReverbUpRoomSize:return roomNames;
        case Param::ReverbUpTime:return timeNames;
        case Param::ReverbDownRoomSize:return roomNames;
        case Param::ReverbDownTime:return timeNames;
        default:break;
    }
    if(p>=Param::IsolateMinLow&&p<=Param::IsolateMinHigh) return isolatorMinNames;
    if(p>=Param::IsolateMaxLow&&p<=Param::IsolateMaxHigh) return isolatorMaxNames;
    if((p>=Param::AddPatternLow&&p<=Param::BandRollPatternHigh)) return patternNames;
    if(p==Param::CutKickStrength||(p>=Param::GateDepthLow&&p<=Param::DriveDepthHigh)) return strengthNames;
    if(parameters[static_cast<size_t>(p)].discrete&&parameters[static_cast<size_t>(p)].max==1) return switchNames;
    return {};
}
inline float sanitize(Param p, float value) noexcept {
    const auto& info = parameters[static_cast<size_t>(p)];
    if (!std::isfinite(value)) value = info.initial;
    value = std::clamp(value, info.min, info.max);
    return info.discrete ? std::round(value) : value;
}
// Both UI labels and DSP resolve Default/User through the same assignment.
// Existing x_roll values still address the same eight strip positions.
inline size_t xPadBeatChoice(const std::array<float,parameterCount>& values,float position) noexcept {
    const auto region=static_cast<size_t>(sanitize(Param::XRoll,position));
    const auto param=static_cast<Param>(static_cast<size_t>(Param::XPadBeat1)+region);
    const auto& info=parameters[static_cast<size_t>(param)];
    return static_cast<size_t>(sanitize(param,values[static_cast<size_t>(Param::UserSettings)]>.5f?values[static_cast<size_t>(param)]:info.initial));
}
inline double xPadDivision(const std::array<float,parameterCount>& values) noexcept {
    return xPadBeatValues[xPadBeatChoice(values,values[static_cast<size_t>(Param::XRoll)])];
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
