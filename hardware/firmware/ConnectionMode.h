#pragma once
#include <cstdint>

namespace rmx::embedded {
// The rear CONNECTION switch selects analog gain, independently of wet/dry
// routing. Call from the foreground; clear the processing request whenever
// ready is false, before writing driveSendReturn to the gain-relay driver.
class ConnectionMode {
  public:
    struct State {
        bool driveSendReturn;
        bool ready;
    };
    static constexpr uint32_t debounceMs = 8, dryWaitMs = 20, settleMs = 30;

    State update(bool sendReturn, uint32_t now) {
        if (!started_ || sendReturn != candidate_) {
            started_ = true;
            candidate_ = sendReturn;
            phase_ = Phase::Debounce;
            since_ = now;
        }
        const uint32_t elapsed = now - since_; // unsigned arithmetic handles wrap
        switch (phase_) {
        case Phase::Debounce:
            if (elapsed >= debounceMs) {
                phase_ = Phase::DryWait;
                since_ = now;
            }
            break;
        case Phase::DryWait:
            if (elapsed >= dryWaitMs) {
                drive_ = candidate_;
                phase_ = Phase::Settle;
                since_ = now;
            }
            break;
        case Phase::Settle:
            if (elapsed >= settleMs)
                phase_ = Phase::Ready;
            break;
        case Phase::Ready:
            break;
        }
        return {drive_, phase_ == Phase::Ready};
    }

  private:
    enum class Phase { Debounce, DryWait, Settle, Ready };
    Phase phase_ = Phase::Debounce;
    bool started_ = false, candidate_ = false, drive_ = false;
    uint32_t since_ = 0;
};
} // namespace rmx::embedded
