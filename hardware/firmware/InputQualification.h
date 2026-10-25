#pragma once
#include <cstdint>

namespace rmx::embedded {
// E11 independently closes the processing-input relay and times its settling.
// This policy adds a continuous quiet interval after observing INPUT_READY.
// Manual bypass is deliberately absent: the input stays warm in dry bypass.
class InputQualification {
  public:
    struct Result {
        bool ready;
        bool fault;
    };
    static constexpr uint32_t quietMs = 1250, timeoutMs = 10000;

    Result update(bool requested, bool hardwareReady, bool statusValid, uint32_t now) {
        if (!statusValid)
            fault_ = true;
        if (fault_)
            return {false, true};
        if (!requested) {
            phase_ = Phase::Idle;
            return {false, false};
        }
        if (phase_ == Phase::Ready) {
            if (hardwareReady)
                return {true, false};
            // A loss after hours of operation gets a fresh recovery deadline.
            phase_ = Phase::Waiting;
            since_ = now;
        }
        if (phase_ == Phase::Idle) {
            phase_ = Phase::Waiting;
            since_ = now;
        }
        if (static_cast<uint32_t>(now - since_) >= timeoutMs) {
            fault_ = true;
            return {false, true};
        }
        if (!hardwareReady)
            phase_ = Phase::Waiting;
        else if (phase_ == Phase::Waiting) {
            phase_ = Phase::Quiet;
            quietSince_ = now;
        } else if (static_cast<uint32_t>(now - quietSince_) >= quietMs)
            phase_ = Phase::Ready;
        return {phase_ == Phase::Ready, false};
    }

  private:
    enum class Phase { Idle, Waiting, Quiet, Ready };
    Phase phase_ = Phase::Idle;
    uint32_t since_ = 0, quietSince_ = 0;
    bool fault_ = false;
};
} // namespace rmx::embedded
