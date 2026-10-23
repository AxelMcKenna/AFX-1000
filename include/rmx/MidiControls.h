#pragma once
#include "Engine.h"
#include "State.h"

namespace rmx {
// MIDI decoding belongs to adapters. Mapping, pickup and transport rules are
// shared and run exclusively on the audio thread. Mapping/learn requests are atomic.
class MidiControls {
  public:
    std::array<std::atomic<int>, 128> cc;
    std::atomic<int> learnTarget{-1}, learnedCC{-1};

    MidiControls() {
        const State defaults;
        for (size_t i = 0; i < cc.size(); ++i)
            cc[i].store(defaults.cc[i]);
        reset();
    }
    void reset() noexcept {
        last.fill(-1);
        mapped.fill(-1);
        pickedUp.fill(false);
        clockPlaying = false;
        haveClock = false;
        clockBeat = 0;
        clockBpm = 120;
    }

    template <class Send>
    void process(uint8_t status, uint8_t a, uint8_t b, double seconds, ParameterStore& params,
                 Send send) noexcept {
        if (a >= 128 || b >= 128)
            return;
        if ((status & 0xf0) == 0x90 && b && a >= 36 && a <= 39)
            send(Event{EventType::Trigger, static_cast<uint8_t>(a - 36), b / 127.f});
        if ((status & 0xf0) == 0xb0) {
            const int learning = learnTarget.exchange(-1);
            if (learning >= 0 && learning < static_cast<int>(parameterCount)) {
                cc[a].store(learning);
                learnedCC.store(a);
                pickedUp[a] = false;
                last[a] = -1;
            }
            const int index = cc[a].load();
            if (index != mapped[a]) {
                mapped[a] = index;
                pickedUp[a] = false;
                last[a] = -1;
            }
            if (index >= 0 && index < static_cast<int>(parameterCount)) {
                const auto p = static_cast<Param>(index);
                const auto& info = parameters[static_cast<size_t>(index)];
                const float value = b / 127.f;
                const float current = (params.get(p) - info.min) / (info.max - info.min);
                if (std::abs(value - current) < .035f ||
                    (last[a] >= 0 && (last[a] - current) * (value - current) <= 0))
                    pickedUp[a] = true;
                last[a] = value;
                if (pickedUp[a])
                    params.set(p, info.min + value * (info.max - info.min));
            }
            if (a == 64)
                send(Event{b >= 64 ? EventType::RollStart : EventType::RollStop});
            if (a == 123)
                send(Event{EventType::Panic});
        }
        if (status == 0xfa) {
            clockPlaying = true;
            clockBeat = 0;
            haveClock = false;
        }
        if (status == 0xfb)
            clockPlaying = true;
        if (status == 0xfc) {
            clockPlaying = false;
            send(Event{EventType::RollStop});
        }
        if (status == 0xf8 && std::isfinite(seconds)) {
            if (haveClock && seconds > lastClock) {
                const double tempo = 60 / (24 * (seconds - lastClock));
                if (tempo >= 40 && tempo <= 240)
                    clockBpm += (tempo - clockBpm) * .15;
            }
            lastClock = seconds;
            haveClock = true;
            clockBeat += 1. / 24;
        }
    }

    Transport transport(double seconds) const noexcept {
        Transport result;
        if (clockPlaying && haveClock && seconds - lastClock < .5) {
            result.synced = true;
            result.bpm = clockBpm;
            result.beat = std::max(0., clockBeat + (seconds - lastClock) * clockBpm / 60);
        }
        return result;
    }

  private:
    std::array<float, 128> last{};
    std::array<int, 128> mapped{};
    std::array<bool, 128> pickedUp{};
    double lastClock{}, clockBpm{120}, clockBeat{};
    bool clockPlaying{}, haveClock{};
};
} // namespace rmx
