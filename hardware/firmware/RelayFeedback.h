#pragma once
#include <cstdint>

namespace rmx::embedded {
// Wait after every ineligible state, including manual bypass and calibration.
// In particular, do not emit a latch clock while the manual switch's other pole
// may still be changing state or bouncing.
class RearmDelay {
  public:
    static constexpr uint32_t stableMs = 350;
    bool update(bool eligible, uint32_t now) {
        if (!eligible) {
            waiting_ = false;
            return false;
        }
        if (!waiting_) {
            waiting_ = true;
            since_ = now;
        }
        return static_cast<uint32_t>(now - since_) >= stableMs;
    }

  private:
    bool waiting_ = false;
    uint32_t since_ = 0;
};

// Monitor E02's latch Q. This is feedback/diagnosis; the independent hardware
// latch and AND gate still decide whether the physical bypass coils energize.
class RelayFeedback {
  public:
    struct Result {
        bool allowPermit;
        bool fault;
    };
    static constexpr uint32_t responseMs = 20;

    Result update(bool desired, bool armed, uint32_t now) {
        if (!desired) {
            active_ = seen_ = missing_ = false;
            return {false, false};
        }
        if (!active_) {
            active_ = true;
            since_ = now;
        }
        if (armed) {
            seen_ = true;
            missing_ = false;
            return {true, false};
        }
        if (seen_) {
            if (!missing_) {
                missing_ = true;
                since_ = now;
            }
            // Drop permit immediately, but allow the two poles of the manual
            // switch time to agree before diagnosing a latched hardware fault.
            return {false, static_cast<uint32_t>(now - since_) >= responseMs};
        }
        const bool timeout = static_cast<uint32_t>(now - since_) >= responseMs;
        // Initial arming needs one callback-driven positive permit edge.
        return {!timeout, timeout};
    }

  private:
    bool active_ = false, seen_ = false, missing_ = false;
    uint32_t since_ = 0;
};
} // namespace rmx::embedded
