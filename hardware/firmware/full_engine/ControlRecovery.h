#pragma once
#include <array>
#include <cmath>
#include <cstdint>

namespace rmx::embedded {
// A foreground event gate, not a replacement for converter, calibration,
// watchdog, relay feedback, debouncing or the 350 ms processing rearm policy.
class ControlRecovery {
  public:
    static constexpr uint32_t buttonMask = (uint32_t{1} << 29) - 1;
    static constexpr uint32_t releaseStableMs = 5; // Existing button debounce interval.
    static constexpr uint32_t touchFreshMs = 20;   // Existing callback control-freshness limit.
    struct Frame {
        uint32_t now{}, keys{};
        // Supply all required non-touch checks before calling update, including
        // rear I/O, current angle validity/plausibility and foreground timing.
        bool buttonsValid{}, otherValid{};
        bool touchSampled{}, touchValid{}, touchActive{};
        float touchPosition{};
        // True only for a valid lever at its existing calibrated home threshold.
        bool leverHome{};
    };
    struct Result {
        bool healthy{}, dispatch{}, reprime{}, clearGestures{};
        uint32_t keys{}, blockedButtons{};
        bool touchUpdated{}, touchActive{}, releaseAllowed{};
        float touchPosition{};
    };
    Result update(const Frame& frame) noexcept {
        if (frame.touchSampled) {
            touchValid_ = frame.touchValid &&
                          (!frame.touchActive || (std::isfinite(frame.touchPosition) &&
                                                  frame.touchPosition >= 0 && frame.touchPosition <= 1));
            if (touchValid_) {
                lastTouch_ = frame.now;
                touchActive_ = frame.touchActive;
                touchPosition_ = frame.touchActive ? frame.touchPosition : 0;
            }
        }
        if (touchValid_ && static_cast<uint32_t>(frame.now - lastTouch_) > touchFreshMs)
            touchValid_ = false;
        // Check the raw selector first: neither endpoint means Echo, one means
        // Back Spin/Brake, and both is invalid. No button event is dispatched
        // from a frame later discovered to have conflicting selector contacts.
        const bool selectorsValid = (frame.keys & (uint32_t{3} << 30)) != (uint32_t{3} << 30);
        const bool valid = frame.buttonsValid && frame.otherValid && selectorsValid && touchValid_;
        Result result;
        if (!valid) {
            result.clearGestures = !recovering_ || firstClear_;
            firstClear_ = false;
            recovering_ = true;
            touchBlocked_ = leverBlocked_ = true;
            releaseTracking_ = 0;
            return result;
        }
        result.healthy = true;
        if (recovering_) {
            recovering_ = false;
            result.reprime = true;
            result.clearGestures = firstClear_;
            firstClear_ = false;
            blockedButtons_ = frame.keys & buttonMask;
            releaseTracking_ = 0;
            touchBlocked_ = leverBlocked_ = true;
        }
        for (unsigned bit = 0; bit < 29; ++bit) {
            const uint32_t mask = uint32_t{1} << bit;
            if (!(blockedButtons_ & mask))
                continue;
            if (frame.keys & mask) {
                releaseTracking_ &= ~mask;
            } else if (!(releaseTracking_ & mask)) {
                releaseTracking_ |= mask;
                releasedAt_[bit] = frame.now;
            } else if (static_cast<uint32_t>(frame.now - releasedAt_[bit]) >= releaseStableMs) {
                blockedButtons_ &= ~mask;
                releaseTracking_ &= ~mask;
            }
        }
        if (frame.touchSampled && touchValid_ && !touchActive_)
            touchBlocked_ = false;
        if (frame.leverHome)
            leverBlocked_ = false;
        result.keys = frame.keys & ~blockedButtons_;
        result.blockedButtons = blockedButtons_;
        result.releaseAllowed = !leverBlocked_;
        // A re-prime frame only initializes state; it never emits actions.
        result.dispatch = !result.reprime;
        result.touchUpdated = result.dispatch && frame.touchSampled && touchValid_;
        result.touchActive = !touchBlocked_ && touchActive_;
        result.touchPosition = result.touchActive ? touchPosition_ : 0;
        return result;
    }

  private:
    std::array<uint32_t, 29> releasedAt_{};
    uint32_t blockedButtons_{}, releaseTracking_{}, lastTouch_{};
    bool recovering_{true}, firstClear_{true}, touchValid_{}, touchActive_{};
    bool touchBlocked_{true}, leverBlocked_{true};
    float touchPosition_{};
};
} // namespace rmx::embedded
