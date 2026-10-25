#pragma once
#include <cstdint>

namespace rmx::embedded {
// E09 CHIP_EN may remain low while E13/rail generation settles. A NACK is
// expected in this bounded, pre-audio phase only. A responding wrong ID faults;
// all configuration/readback failures after this phase keep their hard fault.
template <class Bus> class ConverterPower {
  public:
    enum class State { Waiting, Ready, Fault };
    static constexpr uint32_t pollMs = 5, stableMs = 20, timeoutMs = 5000;
    explicit ConverterPower(Bus& bus) : bus_(bus) {}
    State poll(uint32_t now) {
        if (state_ != State::Waiting)
            return state_;
        if (!started_) {
            started_ = true;
            since_ = now;
            lastPoll_ = now - pollMs;
        }
        if (static_cast<uint32_t>(now - since_) >= timeoutMs)
            return state_ = State::Fault;
        if (static_cast<uint32_t>(now - lastPoll_) < pollMs)
            return state_;
        lastPoll_ = now;
        uint8_t id = 0;
        if (!bus_.codecRead(225, id)) {
            responding_ = false;
            return state_;
        }
        if (id != 0xaf)
            return state_ = State::Fault;
        if (!responding_) {
            responding_ = true;
            readySince_ = now;
        }
        if (static_cast<uint32_t>(now - readySince_) >= stableMs)
            state_ = State::Ready;
        return state_;
    }

  private:
    Bus& bus_;
    State state_ = State::Waiting;
    bool started_ = false, responding_ = false;
    uint32_t since_ = 0, lastPoll_ = 0, readySince_ = 0;
};
} // namespace rmx::embedded
