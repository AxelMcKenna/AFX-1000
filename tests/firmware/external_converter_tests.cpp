#include "hardware/firmware/BoardProfile.h"
#include "hardware/firmware/ConverterPower.h"
#include "hardware/firmware/DmaHalf.h"
#include "hardware/firmware/Es9292.h"
#include "hardware/firmware/Pcm32.h"
#include "hardware/firmware/RelayFeedback.h"
#include <array>
#include <bit>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <utility>
#include <vector>

namespace {
static_assert(rmx::embedded::externalConverter && rmx::embedded::permitPin == 29 &&
              rmx::embedded::armedPin == 30 && rmx::embedded::resetPin == 0);
void require(bool value, const char* message) {
    if (!value)
        throw std::runtime_error(message);
}
// Transport fault injector, not an analog/clock simulation. Paired registers
// commit only on their MSB, exercising the datasheet's actual ordering rule.
struct Bus {
    std::array<uint8_t, 256> reg{}, pending{};
    std::vector<std::pair<uint8_t, uint8_t>> writes;
    size_t operations = 0, failAt = 0, corruptWrite = 0;
    Bus() {
        reg.fill(0xa5);
        reg[225] = 0xaf;
        goodStatus();
    }
    void goodStatus() {
        reg[218] = 1;
        reg[219] = 1;
        reg[221] = 0x81;
        reg[241] = 0x30;
    }
    static bool low(uint8_t r) {
        for (uint8_t base : {12, 14, 66, 68, 70, 72, 74, 83, 89, 110, 112, 118})
            if (r == base)
                return true;
        return false;
    }
    bool codecRead(uint8_t r, uint8_t& value) {
        if (++operations == failAt)
            return false;
        value = reg[r];
        return true;
    }
    bool codecWrite(uint8_t r, uint8_t value) {
        if (++operations == failAt)
            return false;
        writes.emplace_back(r, value);
        if (writes.size() == corruptWrite)
            value ^= 1;
        if (low(r))
            pending[r] = value;
        else if (r && low(r - 1)) {
            reg[r - 1] = pending[r - 1];
            reg[r] = value;
        } else
            reg[r] = value;
        return true;
    }
};
using Codec = rmx::embedded::Es9292<Bus>;
using Session = rmx::embedded::ConverterSession<Bus>;
size_t faultCases = 0;
void powerQualification() {
    struct PowerBus : Bus {
        bool awake = false;
        bool codecRead(uint8_t reg, uint8_t& value) {
            if (!awake)
                return false;
            return Bus::codecRead(reg, value);
        }
    };
    using Power = rmx::embedded::ConverterPower<PowerBus>;
    using PowerState = Power::State;
    static_assert(Power::pollMs == 5 && Power::stableMs == 20 && Power::timeoutMs == 5000);
    for (uint32_t start : std::array<uint32_t, 3>{0, 0xfffffff0u, 0xffff0000u}) {
        for (uint32_t wake : std::array<uint32_t, 4>{0, 180, 420, 4000}) {
            PowerBus bus;
            Power power(bus);
            for (uint32_t t = 0; t <= wake + 20; ++t) {
                bus.awake = t >= wake;
                const auto state = power.poll(start + t);
                require(state == (t == wake + 20 ? PowerState::Ready : PowerState::Waiting),
                        "Power wait ignored delayed hardware enable or continuous ID interval");
                require(bus.writes.empty(),
                        "Codec configuration began while hardware still held it disabled");
            }
            rmx::embedded::ConverterSession<PowerBus> session(bus);
            require(session.prepare(start + wake + 21),
                    "Real converter session failed after delayed power qualification");
        }
        PowerBus bus;
        Power bounce(bus);
        bus.awake = true;
        bounce.poll(start);
        bounce.poll(start + 15);
        bus.awake = false;
        require(bounce.poll(start + 20) == PowerState::Waiting,
                "Missing codec did not restart startup quiet");
        bus.awake = true;
        bounce.poll(start + 25);
        require(bounce.poll(start + 40) == PowerState::Waiting &&
                    bounce.poll(start + 45) == PowerState::Ready,
                "Interrupted chip-enable interval did not require fresh continuous responses");
        PowerBus missing;
        Power timeout(missing);
        require(timeout.poll(start) == PowerState::Waiting &&
                    timeout.poll(start + 4999) == PowerState::Waiting &&
                    timeout.poll(start + 5000) == PowerState::Fault,
                "Absent codec startup was unbounded or timed out early");
        missing.awake = true;
        require(timeout.poll(start + 5001) == PowerState::Fault, "Startup timeout did not stay latched");
        PowerBus chatter;
        Power neverStable(chatter);
        for (uint32_t t = 0; t <= 5000; t += 5) {
            chatter.awake = t % 20 != 0;
            require(neverStable.poll(start + t) == (t == 5000 ? PowerState::Fault : PowerState::Waiting),
                    "Chattering codec responses extended startup deadline");
        }
        PowerBus wrong;
        wrong.awake = true;
        wrong.reg[225] = 0x42;
        Power bad(wrong);
        require(bad.poll(start) == PowerState::Fault,
                "Responding wrong device was retried as an unpowered codec");
    }
}
void settingsAndFailures() {
    Bus bus;
    Codec codec(bus);
    require(codec.prepare(), "Muted codec configuration failed");
    const size_t count = bus.operations, writeCount = bus.writes.size();
    // Independent end-state contract: 512fs MCLK, 64fs stereo I2S, unity gain,
    // normal channel polarity, no direct monitoring, no silence-induced DC shift.
    require((bus.reg[0] & 0xbf) == 0x2f && (bus.reg[1] & 0x17) == 2 && (bus.reg[5] & 0x7f) == 3 &&
                (bus.reg[6] & 0x10) == 0 && bus.reg[7] == 7 && (bus.reg[9] & 0xbf) == 0x25,
            "Clock/master configuration disagrees with E09");
    require((bus.reg[10] & 0x5f) == 1 && (bus.reg[11] & 0x7f) == 0 && (bus.reg[12] & 31) == 0 &&
                (bus.reg[13] & 31) == 1 && (bus.reg[14] & 31) == 0 && (bus.reg[15] & 31) == 1,
            "I2S slots/width/order are wrong");
    require((bus.reg[116] & 0x33) == 0x33 && (bus.reg[68]) == 0 && (bus.reg[69] & 1) == 0,
            "Setup exposed an unmuted path or qualified flag");
    require(bus.reg[110] == 2 && bus.reg[111] == 2 && bus.reg[112] == 255 && bus.reg[113] == 255 &&
                (bus.reg[117] & 0x6f) == 3 && (bus.reg[120] & 3) == 0,
            "Silence can move bias or bypass DSP");
    require(bus.reg[62] == 0x62 && (bus.reg[77] & 0x7f) == 4, "Qualification flag source is wrong");
    for (auto s : Codec::settings) {
        uint16_t mask = s.mask;
        for (uint8_t i = 0; i < s.count; ++i) {
            const uint8_t reserved = ~static_cast<uint8_t>(mask >> (8 * i));
            require((bus.reg[s.reg + i] & reserved) == (0xa5 & reserved), "Reserved bits were overwritten");
        }
    }
    for (size_t i = 0; i < bus.writes.size(); ++i)
        if (Bus::low(bus.writes[i].first))
            require(i + 1 < bus.writes.size() && bus.writes[i + 1].first == bus.writes[i].first + 1,
                    "Multi-byte register did not write LSB immediately before MSB");
    require(codec.activateSilentStream(), "Silent DMA activation failed");
    require((bus.reg[116] & 0x33) == 0x30 && bus.reg[68] == 12, "Activation did not preserve direct mute");
    const auto end = bus.writes.size();
    size_t unmute = 0, flags = 0;
    for (size_t i = writeCount; i < end; ++i) {
        if (bus.writes[i].first == 116)
            unmute = i;
        if (bus.writes[i].first == 68)
            flags = i;
    }
    require(unmute < flags, "Hardware qualification started before DAC unmute");
    require(!codec.activateSilentStream(), "Repeated activation rewrote DC state");
    for (size_t i = 1; i <= count; ++i) {
        Bus faulty;
        faulty.failAt = i;
        Session session(faulty);
        require(!session.prepare(0) && session.state() == Session::State::Fault,
                "Setup I2C fault was ignored");
        require(session.poll(9000, 500, true, true) == Session::State::Fault,
                "Setup fault automatically recovered");
        ++faultCases;
    }
    for (size_t i = 1; i <= writeCount; ++i) {
        Bus faulty;
        faulty.corruptWrite = i;
        Session session(faulty);
        require(!session.prepare(0), "Corrupted write escaped readback verification");
        ++faultCases;
    }
    Bus wrong;
    wrong.reg[225] = 0;
    Session rejected(wrong);
    require(!rejected.prepare(0) && wrong.writes.empty(), "Wrong chip ID received register writes");
}
void qualification() {
    Bus bus;
    Session session(bus);
    require(session.prepare(0), "Session failed to prepare");
    for (uint32_t t = 0; t < 4; ++t)
        require(session.poll(t, t, true, true) == Session::State::Silent,
                "DAC enabled before four silent callbacks");
    require(session.poll(4, 4, true, true) == Session::State::Settling,
            "Silent stream did not start settling");
    // Premature high status cannot bypass the minimum quiet interval.
    for (uint32_t t = 5; t < 1215; ++t)
        require(session.poll(t, t, true, true) == Session::State::Settling,
                "Premature hardware high bypassed quiet interval");
    require(session.poll(1215, 1215, true, true) == Session::State::Ready,
            "Qualified stream never became ready");
    require(session.poll(1216, 1216, true, false) == Session::State::Fault,
            "Lost ANALOG_OK did not revoke readiness");
    require(session.poll(1217, 1217, true, true) == Session::State::Fault,
            "Qualifier loss recovered without restart");

    Bus slow;
    Session delayed(slow);
    require(delayed.prepare(0), "Delayed session setup failed");
    for (uint32_t t = 0; t <= 5000; ++t)
        delayed.poll(t, t, true, false);
    require(!delayed.ready() && delayed.state() == Session::State::Settling,
            "Slow hardware timer caused premature fault/permit");
    require(delayed.poll(5001, 5001, true, true) == Session::State::Ready,
            "Real delayed qualification was rejected");
    // Calibration retains DC bias but requires a fresh silent callback warmup.
    const auto writes = slow.writes.size();
    delayed.restartSilent(5010);
    require(delayed.poll(5011, 0, true, true) == Session::State::Silent,
            "Calibration restart reused stale callbacks");
    require(delayed.poll(5020, 4, true, true) == Session::State::Settling,
            "Calibration DMA failed to resume");
    for (uint32_t t = 5021; t < 6231; ++t)
        require(delayed.poll(t, t, true, true) == Session::State::Settling,
                "Calibration quiet interval shortened");
    require(delayed.poll(6231, 6231, true, true) == Session::State::Ready && slow.writes.size() == writes,
            "Calibration rewrote analog configuration or failed to requalify");

    Bus timeout;
    Session absent(timeout);
    absent.prepare(0);
    require(absent.poll(7999, 0, true, false) == Session::State::Silent, "Missing callbacks timed out early");
    require(absent.poll(8000, 0, true, false) == Session::State::Fault, "Missing callbacks never timed out");
    Bus late;
    Session lateFirstPoll(late);
    lateFirstPoll.prepare(0);
    require(lateFirstPoll.poll(9000, 3000, true, true) == Session::State::Fault,
            "Late first callback bypassed startup timeout");
    Bus timer;
    Session neverReady(timer);
    neverReady.prepare(0);
    neverReady.poll(10, 4, true, false);
    require(neverReady.poll(8009, 8009, true, false) == Session::State::Settling &&
                neverReady.poll(8010, 8010, true, false) == Session::State::Fault,
            "Missing ANALOG_OK never timed out");

    Bus bounce;
    Session interrupted(bounce);
    interrupted.prepare(0);
    for (uint32_t t = 0; t <= 1000; ++t)
        interrupted.poll(t, t, true, true);
    bounce.reg[241] = 0xc0;
    interrupted.poll(1001, 1001, true, true);
    bounce.goodStatus();
    for (uint32_t t = 1002; t < 2213; ++t)
        require(interrupted.poll(t, t, true, true) == Session::State::Settling,
                "Ramp interruption did not restart quiet interval");
    require(interrupted.poll(2213, 2213, true, true) == Session::State::Ready,
            "Quiet interval never recovered after ramp interruption");

    Bus wrap;
    Session wrapped(wrap);
    constexpr uint32_t start = 0xfffffff0u;
    wrapped.prepare(start);
    wrapped.poll(start + 4, 4, true, false);
    for (uint32_t t = 5; t < 1215; ++t)
        wrapped.poll(start + t, t, true, false);
    require(wrapped.poll(start + 1215, 1215, true, true) == Session::State::Ready,
            "Qualification failed across timer wrap");

    // The real relay policies must see zero enable edges during a long analog
    // settle, then produce exactly one edge after continuous stable eligibility.
    Bus interlock;
    Session qualified(interlock);
    qualified.prepare(0);
    rmx::embedded::RearmDelay rearm;
    rmx::embedded::RelayFeedback relay;
    bool q = false, oldPermit = false;
    unsigned edges = 0;
    for (uint32_t t = 0; t < 5500; ++t) {
        qualified.poll(t, t, true, t >= 5000);
        const auto result = relay.update(rearm.update(qualified.ready(), t), q, t);
        require(!result.fault, "Expected hardware settling tripped relay feedback timeout");
        if (result.allowPermit && !oldPermit) {
            q = true;
            ++edges;
            require(t >= 5350, "Permit preceded stable qualification");
        }
        oldPermit = result.allowPermit;
    }
    require(edges == 1 && q, "Qualified startup did not produce exactly one permit edge");
}
void runningFaults() {
    // Fail every read/write in the activation, live-status and audit paths.
    Bus sample;
    Session baseline(sample);
    baseline.prepare(0);
    const size_t before = sample.operations;
    baseline.poll(4, 4, true, false);
    for (size_t i = before + 1; i <= sample.operations; ++i) {
        Bus bus;
        Session session(bus);
        session.prepare(0);
        bus.failAt = i;
        require(session.poll(4, 4, true, false) == Session::State::Fault,
                "Activation/status I2C fault was ignored");
        ++faultCases;
    }
    for (unsigned mode = 0; mode < 9; ++mode) {
        Bus bus;
        Session session(bus);
        session.prepare(0);
        for (uint32_t t = 0; t <= 1215; ++t)
            session.poll(t, t, true, true);
        require(session.ready(), "Running-fault setup never qualified");
        switch (mode) {
        case 0:
            bus.reg[218] = 0;
            break;
        case 1:
            bus.reg[219] = 0;
            break;
        case 2:
            bus.reg[221] = 0x01;
            break;
        case 3:
            bus.reg[221] = 0xc1;
            break;
        case 4:
            bus.reg[221] = 0xa1;
            break;
        case 5:
            bus.reg[241] = 0;
            break;
        case 6:
            bus.reg[241] = 0xc0;
            break; // Ramp done but fully DOWN.
        case 7:
            bus.reg[241] = 0x10;
            break; // Only left channel up.
        case 8:
            bus.reg[241] = 0x34;
            break; // Unexpected automute.
        }
        require(session.poll(1216, 1216, true, true) == Session::State::Fault,
                "Live converter failure did not revoke readiness");
    }
    Bus stale;
    Session stalled(stale);
    stalled.prepare(0);
    for (uint32_t t = 0; t <= 1215; ++t)
        stalled.poll(t, t, true, true);
    require(stalled.poll(1235, 1215, true, true) == Session::State::Ready &&
                stalled.poll(1236, 1215, true, true) == Session::State::Fault,
            "Stalled DMA was not detected");
    Bus bad;
    Session disconnected(bad);
    disconnected.prepare(0);
    require(disconnected.poll(1, 0, false, false) == Session::State::Fault,
            "Failed rear expander was accepted");
    Bus changed;
    Session audit(changed);
    audit.prepare(0);
    for (uint32_t t = 0; t <= 1215; ++t)
        audit.poll(t, t, true, true);
    changed.reg[112] = 2; // Forbidden direct-monitor route may not survive an audit.
    for (uint32_t t = 1216; t < 1300 && audit.ready(); ++t)
        audit.poll(t, t, true, true);
    require(audit.state() == Session::State::Fault, "Configuration corruption escaped rolling audit");
    for (auto setting : Codec::settings) {
        Bus bus;
        Session monitored(bus);
        monitored.prepare(0);
        for (uint32_t t = 0; t <= 1215; ++t)
            monitored.poll(t, t, true, true);
        require(monitored.ready(), "Configuration audit setup failed");
        const unsigned bit = std::countr_zero(static_cast<unsigned>(setting.mask));
        bus.reg[setting.reg + bit / 8] ^= 1u << (bit % 8);
        for (uint32_t t = 1216; t < 1300 && monitored.ready(); ++t)
            monitored.poll(t, t, true, true);
        require(monitored.state() == Session::State::Fault, "A controlled configuration bit escaped audit");
        ++faultCases;
    }
}
void pcm() {
    using rmx::embedded::decodePcm32;
    using rmx::embedded::encodePcm32;
    // The transport must discard unsettled ADC samples before they can enter
    // DSP histories, then resume with correct stereo order and signed scale.
    std::array<int32_t, 6> input{INT32_MAX, INT32_MIN, 1073741824, -1073741824, 0, 536870912};
    std::array<float, 3> left{1, 1, 1}, right{-1, -1, -1};
    rmx::embedded::decodeStereoPcm32(input.data(), left.data(), right.data(), 3, false);
    require(left == std::array<float, 3>{0, 0, 0} && right == std::array<float, 3>{0, 0, 0},
            "Unqualified ADC transients entered DSP histories");
    rmx::embedded::decodeStereoPcm32(input.data(), left.data(), right.data(), 3, true);
    require(left == std::array<float, 3>{decodePcm32(INT32_MAX), .5f, 0} &&
                right == std::array<float, 3>{-1, -.5f, .25f},
            "Qualified stereo PCM order or scale changed");
    require(encodePcm32(1) == INT32_MAX && encodePcm32(-1) == INT32_MIN && encodePcm32(3) == INT32_MAX &&
                encodePcm32(-3) == INT32_MIN,
            "PCM endpoints overflowed");
    require(encodePcm32(std::nanf("")) == 0 && encodePcm32(INFINITY) == 0, "Nonfinite PCM was not silenced");
    require(encodePcm32(.5f) == 1073741824 && encodePcm32(-.5f) == -1073741824 &&
                decodePcm32(INT32_MIN) == -1 && decodePcm32(1073741824) == .5f,
            "PCM signed scale is wrong");
    for (int i = -10000; i <= 10000; ++i) {
        const float v = i / 10000.f;
        require(std::abs(decodePcm32(encodePcm32(v)) - v) < 1e-7f, "PCM roundtrip lost float precision");
    }
    using rmx::embedded::transmitHalfAvailable;
    for (uint32_t remaining = 0; remaining <= 513; ++remaining) {
        const bool first = transmitHalfAvailable(0, remaining),
                   second = transmitHalfAvailable(256, remaining);
        require(!(first && second), "Both TX halves became writable simultaneously");
        require(!first || (remaining <= 256 && remaining >= 16),
                "TX first half overlaps active data / guard");
        require(!second || (remaining >= 272 && remaining <= 512),
                "TX second half overlaps active data / guard");
        require(!transmitHalfAvailable(128, remaining), "Invalid TX half offset was accepted");
    }
    require(transmitHalfAvailable(0, 256) && transmitHalfAvailable(0, 16) &&
                transmitHalfAvailable(256, 512) && transmitHalfAvailable(256, 272),
            "Valid DMA phase boundaries were rejected");
}
} // namespace
int main() {
    try {
        powerQualification();
        settingsAndFailures();
        qualification();
        runningFaults();
        pcm();
        std::cout << "External converter: " << faultCases
                  << " injected setup/activation faults; delayed power/ID startup, settling, live "
                     "clock/ramp, relay, restart, wrap and PCM checks passed\n";
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
