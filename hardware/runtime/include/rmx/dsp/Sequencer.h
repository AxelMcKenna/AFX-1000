#pragma once
#include "Primitives.h"
namespace rmx::dsp {
class Sequencer {
  public:
    void reset() noexcept {
        pendingCount = 0;
        clear();
        rollPad = -1;
        rollNext = 0;
        lastTick = -1;
    }
    void clear() noexcept {
        sequence = {};
        sequenceSize = 0;
    }
    bool rolling() const noexcept {
        return rollPad >= 0;
    }
    void startRoll(uint8_t pad, double beat) noexcept {
        rollPad = pad % 4;
        rollNext = beat;
    }
    void stopRoll() noexcept {
        rollPad = -1;
    }
    bool schedule(int pad, float velocity, const Context& ctx) noexcept {
        double distance = 0;
        if (ctx.get(Param::Quantize) > .5f) {
            double target = std::ceil(ctx.beat * 4 - 1.e-7) / 4;
            if (static_cast<int>(std::round(target * 4)) % 2)
                target += ctx.get(Param::Swing) * .25;
            distance = std::max(0., target - ctx.beat) * 60 / ctx.bpm * ctx.sr;
        }
        if (pendingCount == pending.size())
            return false;
        pending[pendingCount++] = {ctx.frame + static_cast<uint64_t>(distance), static_cast<uint8_t>(pad % 4),
                                   velocity, ctx.get(Param::Overdub) > .5f};
        return true;
    }
    template <class Trigger> void process(const Context& ctx, bool playing, Trigger trigger) noexcept {
        const int tick = static_cast<int>(std::floor(ctx.beat * 24 + 1.e-7)) % 384;
        if (tick != lastTick && playing) {
            for (size_t j = 0; j < sequenceSize; ++j)
                if (sequence[j].active && sequence[j].tick == tick)
                    trigger(sequence[j].pad, sequence[j].velocity);
            lastTick = tick;
        }
        for (size_t j = 0; j < pendingCount;) {
            if (pending[j].at <= ctx.frame) {
                const auto pendingEvent = pending[j];
                trigger(pendingEvent.pad, pendingEvent.velocity);
                if (pendingEvent.record && sequenceSize < sequence.size()) {
                    const auto recordedTick =
                        static_cast<uint16_t>(static_cast<int>(std::round(ctx.beat * 24)) % 384);
                    sequence[sequenceSize++] = {pendingEvent.pad, pendingEvent.velocity, recordedTick, true};
                }
                pending[j] = pending[--pendingCount];
            } else
                ++j;
        }
        if (rollPad >= 0 && ctx.beat >= rollNext) {
            trigger(rollPad, 1);
            rollNext = ctx.beat + beatDivisions[static_cast<size_t>(ctx.get(Param::XRoll))];
        }
    }

  private:
    struct Pending {
        uint64_t at{};
        uint8_t pad{};
        float velocity{};
        bool record{};
    };
    struct Step {
        uint8_t pad{};
        float velocity{};
        uint16_t tick{};
        bool active{};
    };
    std::array<Pending, 64> pending{};
    size_t pendingCount{};
    std::array<Step, 128> sequence{};
    size_t sequenceSize{};
    double rollNext{};
    int rollPad{-1}, lastTick{-1};
};
} // namespace rmx::dsp
