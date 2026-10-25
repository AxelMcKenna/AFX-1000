#pragma once
#include "rmx/Engine.h"
#include "rmx/ControlSurface.h"

namespace rmx::hardware {
// Physical input order is the wiring contract. IDs match hardware/cad/generate.py.
enum class Knob : uint8_t {
    Input,
    Output,
    Low,
    Mid,
    High,
    SceneDepth,
    XLevel,
    XPitch,
    SceneTime,
    SceneResonance,
    Count
};
enum class Button : uint8_t {
    Quantize,
    Auto,
    Tap,
    NudgeDown,
    NudgeUp,
    InputSource,
    PadSource,
    Isolate0,
    Isolate1,
    Isolate2,
    Isolate3,
    Bank,
    Roll,
    Pad0,
    Pad1,
    Pad2,
    Pad3,
    Overdub,
    Hold,
    Scene0,
    Scene1,
    Scene2,
    Scene3,
    Scene4,
    Scene5,
    Scene6,
    Scene7,
    Scene8,
    Scene9,
    Count
};
inline constexpr std::array<std::string_view, 10> knobIds{
    "input",       "output",  "low",     "mid",        "high",
    "scene_depth", "x_level", "x_pitch", "scene_time", "scene_resonance"};
inline constexpr std::array<std::string_view, 29> buttonIds{
    "quantize",    "auto",      "tap",       "nudge_down", "nudge_up",  "source_input",
    "source_xpad", "isolate_0", "isolate_1", "isolate_2",  "isolate_3", "bank",
    "roll",        "pad_0",     "pad_1",     "pad_2",      "pad_3",     "overdub",
    "hold",        "scene_0",   "scene_1",   "scene_2",    "scene_3",   "scene_4",
    "scene_5",     "scene_6",   "scene_7",   "scene_8",    "scene_9"};

class Debouncer {
  public:
    void begin(uint32_t pressed) noexcept {
        raw = stable = pressed;
        changedAt.fill(0);
    }
    uint32_t update(uint32_t pressed, uint32_t now) noexcept {
        const uint32_t changed = raw ^ pressed;
        raw = pressed;
        uint32_t edges = 0;
        for (size_t i = 0; i < 32; ++i) {
            const uint32_t mask = uint32_t(1) << i;
            if (changed & mask)
                changedAt[i] = now;
            if (((raw ^ stable) & mask) && static_cast<uint32_t>(now - changedAt[i]) >= 5) {
                stable ^= mask;
                edges |= mask;
            }
        }
        return edges;
    }
    uint32_t state() const noexcept {
        return stable;
    }

  private:
    uint32_t raw{}, stable{};
    std::array<uint32_t, 32> changedAt{};
};

class Controls {
  public:
    explicit Controls(Engine& value) noexcept : engine(value) {}
    void initializeButtons(uint32_t pressed) noexcept {
        bootHeld = rawDown = pressed & ((uint32_t{1} << 29) - 1);
        surface = {};
        keys = {};
    }
    void knob(Knob id, float normalized) noexcept {
        const size_t index = static_cast<size_t>(id);
        if (index >= last.size() || !std::isfinite(normalized))
            return;
        normalized = std::clamp(normalized, 0.f, 1.f);
        const bool first = !seen[index];
        if (!first && std::abs(normalized - last[index]) < 1.f / 512)
            return;
        last[index] = normalized;
        seen[index] = true;
        constexpr std::array<Param, 10> targets{
            Param::InputGain,  Param::OutputGain, Param::Low,    Param::Mid,       Param::High,
            Param::SceneDepth, Param::XLevel,     Param::XPitch, Param::SceneTime, Param::SceneResonance};
        float value = normalized;
        if (id == Knob::Input || id == Knob::Output)
            value = normalized < .5f ? (normalized - .5f) * 48 : (normalized - .5f) * 24;
        if (id == Knob::Low || id == Knob::Mid || id == Knob::High)
            value = std::abs(normalized - .5f) < .015f ? 0 : normalized * 2 - 1;
        if (id == Knob::XLevel)
            value = normalized * 1.5f;
        if (id == Knob::XPitch)
            value = std::abs(normalized - .5f) < .005f ? 0 : normalized * 48 - 24;
        if (id == Knob::SceneTime)
            value = static_cast<float>(std::min(7, static_cast<int>(normalized * 8)));
        write(targets[index], value);
        // Reading the physical depth at boot must not engage an effect.
        if (id == Knob::SceneDepth && !first)
            write(Param::SceneOn, 1);
    }
    void button(Button id, bool pressed, uint32_t now) noexcept {
        const auto index = static_cast<size_t>(id);
        if (index >= keys.size()) return;
        const uint32_t bit = uint32_t{1} << index;
        if (bool(rawDown & bit) == pressed) return;
        if (pressed) rawDown |= bit; else rawDown &= ~bit;
        if (bootHeld & bit) {
            if (!pressed) bootHeld &= ~bit;
            return;
        }
        auto& key = keys[index];
        if (pressed) {
            key = {now, false, false};
            if (id >= Button::Pad0 && id <= Button::Pad3) {
                const auto pad = index - static_cast<size_t>(Button::Pad0);
                padAt[pad] = now; padLit[pad] = true;
                for (auto modifier : {Button::Overdub, Button::Hold})
                    if (rawDown & (uint32_t{1} << static_cast<size_t>(modifier)))
                        keys[static_cast<size_t>(modifier)].chordUsed = true;
            }
        }
        constexpr std::array<rmx::Button, 29> translated{
            rmx::Button::Quantize, rmx::Button::Auto, rmx::Button::Tap,
            rmx::Button::NudgeMinus, rmx::Button::NudgePlus, rmx::Button::Input,
            rmx::Button::XPad, rmx::Button::Isolator, rmx::Button::CutAdd,
            rmx::Button::TransRoll, rmx::Button::GateDrive, rmx::Button::Bank,
            rmx::Button::Roll, rmx::Button::Kick, rmx::Button::Snare,
            rmx::Button::Clap, rmx::Button::HiHat, rmx::Button::Overdub,
            rmx::Button::Hold, rmx::Button::BpfEcho, rmx::Button::Echo,
            rmx::Button::Noise, rmx::Button::SpiralUp, rmx::Button::ReverbUp,
            rmx::Button::HpfEcho, rmx::Button::LpfEcho, rmx::Button::CrushEcho,
            rmx::Button::SpiralDown, rmx::Button::ReverbDown};
        static_assert(translated.size() == static_cast<size_t>(Button::Count));
        const bool cancelRelease = !pressed && key.longFired;
        surface.button(translated[index], pressed,
            [&](Param p) { return read(p); },
            [&](Param p, float value) {
                if (cancelRelease && ((id == Button::Overdub && p == Param::Overdub) ||
                                      (id == Button::Hold && p == Param::XHold))) return;
                write(p, value);
            },
            [&](Event event) {
                if (cancelRelease && id == Button::Hold && event.type == EventType::RollStop) return;
                send(event);
            });
    }
    void tick(uint32_t now) noexcept {
        for (auto id : {Button::Overdub, Button::Hold}) {
            const auto index = static_cast<size_t>(id);
            const auto bit = uint32_t{1} << index;
            auto& key = keys[index];
            if ((rawDown & bit) && !(bootHeld & bit) && !key.longFired && !key.chordUsed &&
                static_cast<uint32_t>(now - key.at) >= 700) {
                key.longFired = true;
                if (id == Button::Overdub) {
                    write(Param::Overdub, 0); send({EventType::ClearSequence});
                } else toggle(Param::SamplerMute);
            }
        }
    }
    void settings(bool user) noexcept { write(Param::UserSettings, user ? 1.f : 0.f); }
    bool releaseSelection(bool backSpin, bool vinylBrake) noexcept {
        if (backSpin && vinylBrake) return false;
        write(Param::ReleaseType, backSpin ? 0.f : vinylBrake ? 2.f : 1.f); return true;
    }
    void release(float value, bool valid = true) noexcept {
        value = valid && std::isfinite(value) ? std::clamp(value, 0.f, 1.f) : 0;
        write(Param::ReleaseAmount, value < .015f ? 0 : value);
    }
    void touch(float value, bool active) noexcept {
        active = active && std::isfinite(value);
        if (active) write(Param::XRoll, float(std::min(7, int(std::clamp(value, 0.f, 1.f) * 8))));
        surface.touch(active, [&](Event event) { send(event); });
    }
    std::array<uint16_t, 96> feedback(uint32_t now) const noexcept {
        std::array<uint16_t, 96> led{};
        for (size_t i = 0; i < 10; ++i)
            if (read(Param::SceneOn) > .5f && static_cast<size_t>(read(Param::SceneType)) == i)
                led[i] = 4095;
        led[10 + static_cast<size_t>(read(Param::IsolateMode))] = 4095;
        const int source = static_cast<int>(read(Param::SceneSource));
        led[14] = (source == 0 || source == 2) ? 4095 : 0;
        led[15] = (source == 1 || source == 2) ? 4095 : 0;
        for (size_t i = 0; i < 4; ++i)
            if (padLit[i] && static_cast<uint32_t>(now - padAt[i]) < 100)
                led[16 + i] = 4095;
        for (size_t i = 0; i < 5; ++i) {
            constexpr std::array<Param, 5> target{Param::Quantize, Param::AutoTempo, Param::XSource,
                                                  Param::Overdub, Param::XHold};
            led[20 + i] = read(target[i]) > .5f ? 4095 : 0;
        }
        for (size_t row = 0; row < 2; ++row) {
            const float amplitude = row ? engine.meters.output.load(std::memory_order_relaxed)
                                        : engine.meters.input.load(std::memory_order_relaxed);
            const float db = 20 * std::log10(std::max(1.e-8f, amplitude));
            for (size_t i = 0; i < 20; ++i)
                if (db >= -38.f + 2 * static_cast<float>(i))
                    led[25 + 20 * row + i] = 4095;
        }
        if (read(Param::SampleSource) > .5f)
            led[65 + static_cast<size_t>(read(Param::Bank))] = 4095;
        const float tempo = read(Param::AutoTempo) > .5f ? engine.meters.tempo.load(std::memory_order_relaxed)
                                                         : read(Param::Tempo);
        int bpm = std::clamp(static_cast<int>(std::round(tempo)), 0, 999);
        constexpr uint8_t digits[]{0x3f, 0x06, 0x5b, 0x4f, 0x66, 0x6d, 0x7d, 0x07, 0x7f, 0x6f};
        for (int position = 2; position >= 0; --position) {
            const auto mask = digits[bpm % 10];
            bpm /= 10;
            for (int segment = 0; segment < 7; ++segment)
                if (mask & (1 << segment))
                    led[69 + position * 8 + segment] = 4095;
        }
        const auto brightness = static_cast<uint16_t>(600 + 3000 * read(Param::SceneDepth));
        if (read(Param::SceneOn) > .5f && read(Param::SceneType) < 5) {
            led[93] = brightness;
            led[94] = brightness / 3;
        } else {
            led[94] = brightness;
            led[95] = brightness * 3 / 4;
        }
        return led;
    }
  private:
    struct Key { uint32_t at{}; bool longFired{}, chordUsed{}; };
    Engine& engine;
    rmx::ControlSurface surface;
    uint32_t bootHeld{}, rawDown{};
    std::array<Key, 29> keys{};
    std::array<float, 10> last{};
    std::array<bool, 10> seen{};
    std::array<uint32_t, 4> padAt{};
    std::array<bool, 4> padLit{};
    float read(Param p) const noexcept { return engine.params.get(p); }
    void write(Param p, float v) noexcept { engine.params.set(p, v); }
    void toggle(Param p) noexcept { write(p, read(p) > .5f ? 0.f : 1.f); }
    void send(Event event) noexcept { engine.enqueue(event); }
};
} // namespace rmx::hardware
