#pragma once
#include "rmx/Engine.h"
#include "rmx/controls/ControlActions.h"

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
    explicit Controls(Engine& e) noexcept : engine(e) {}
    void initializeButtons(uint32_t pressed) noexcept {
        for (size_t i = 0; i < keys.size(); ++i)
            keys[i] = {bool(pressed & (uint32_t(1) << i)), true, 0};
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
        const size_t index = static_cast<size_t>(id);
        if (index >= keys.size())
            return;
        auto& key = keys[index];
        if (key.down == pressed)
            return;
        key.down = pressed;
        if (!pressed) {
            if (!key.longFired) {
                if (id == Button::Overdub)
                    toggle(Param::Overdub);
                if (id == Button::Hold) {
                    toggle(Param::XHold);
                    if (read(Param::XHold) < .5f)
                        send({EventType::RollStop});
                }
            }
            return;
        }
        key.at = now;
        key.longFired = false;
        if (id == Button::Quantize)
            toggle(Param::Quantize);
        else if (id == Button::Auto)
            toggle(Param::AutoTempo);
        else if (id == Button::Tap)
            send({EventType::Tap});
        else if (id == Button::NudgeDown || id == Button::NudgeUp) {
            write(Param::AutoTempo, 0);
            write(Param::Tempo, read(Param::Tempo) + (id == Button::NudgeUp ? .1f : -.1f));
        } else if (id == Button::InputSource || id == Button::PadSource) {
            toggleRouting(
                id == Button::InputSource ? Source::Input : Source::Pad, [&](Param p) { return read(p); },
                [&](Param p, float v) { write(p, v); });
        } else if (id >= Button::Isolate0 && id <= Button::Isolate3)
            write(Param::IsolateMode, static_cast<float>(index - static_cast<size_t>(Button::Isolate0)));
        else if (id == Button::Bank)
            write(Param::Bank, std::fmod(read(Param::Bank) + 1, 4));
        else if (id == Button::Roll)
            toggle(Param::XSource);
        else if (id >= Button::Pad0 && id <= Button::Pad3) {
            selectedPad = static_cast<uint8_t>(index - static_cast<size_t>(Button::Pad0));
            padAt[selectedPad] = now;
            padLit[selectedPad] = true;
            send({EventType::Trigger, selectedPad});
            if (touching)
                send({EventType::RollStart, selectedPad});
        } else if (id >= Button::Scene0 && id <= Button::Scene9) {
            const float scene = static_cast<float>(index - static_cast<size_t>(Button::Scene0));
            const bool disable = read(Param::SceneOn) > .5f && read(Param::SceneType) == scene;
            write(Param::SceneType, scene);
            write(Param::SceneOn, disable ? 0.f : 1.f);
        }
    }
    void tick(uint32_t now) noexcept {
        for (auto id : {Button::Overdub, Button::Hold}) {
            auto& key = keys[static_cast<size_t>(id)];
            if (key.down && !key.longFired && static_cast<uint32_t>(now - key.at) >= 700) {
                key.longFired = true;
                if (id == Button::Overdub) {
                    write(Param::Overdub, 0);
                    send({EventType::ClearSequence});
                } else
                    toggle(Param::SamplerMute);
            }
        }
    }
    void settings(bool user) noexcept {
        write(Param::UserSettings, user ? 1.f : 0.f);
    }
    bool releaseSelection(bool backSpin, bool vinylBrake) noexcept {
        if (backSpin && vinylBrake)
            return false;
        write(Param::ReleaseType, backSpin ? 0.f : vinylBrake ? 2.f : 1.f);
        return true;
    }
    void release(float normalized, bool sensorValid = true) noexcept {
        normalized = sensorValid && std::isfinite(normalized) ? std::clamp(normalized, 0.f, 1.f) : 0;
        write(Param::ReleaseAmount, normalized < .015f ? 0 : normalized);
    }
    void touch(float normalized, bool active) noexcept {
        active = active && std::isfinite(normalized);
        if (active)
            write(Param::XRoll,
                  static_cast<float>(std::min(7, static_cast<int>(std::clamp(normalized, 0.f, 1.f) * 8))));
        if (active && !touching)
            send({EventType::RollStart, selectedPad});
        if (!active && touching)
            send({EventType::RollStop});
        touching = active;
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
    struct Key {
        bool down{}, longFired{};
        uint32_t at{};
    };
    Engine& engine;
    std::array<float, 10> last{};
    std::array<bool, 10> seen{};
    std::array<Key, 29> keys{};
    std::array<uint32_t, 4> padAt{};
    std::array<bool, 4> padLit{};
    uint8_t selectedPad{};
    bool touching{};
    float read(Param p) const noexcept {
        return engine.params.get(p);
    }
    void write(Param p, float v) noexcept {
        engine.params.set(p, v);
    }
    void toggle(Param p) noexcept {
        write(p, read(p) > .5f ? 0.f : 1.f);
    }
    void send(Event e) noexcept {
        engine.enqueue(e);
    }
};
} // namespace rmx::hardware
