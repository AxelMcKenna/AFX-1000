#include "hardware/firmware/ConnectionMode.h"
#include "hardware/firmware/InputQualification.h"
#include "hardware/firmware/RelayFeedback.h"
#include <array>
#include <iostream>
#include <stdexcept>

using namespace rmx::embedded;
static void require(bool value, const char* message) {
    if (!value)
        throw std::runtime_error(message);
}

static void boundaries(uint32_t start) {
    // All supported hardware delays must finish without consuming the old
    // latch-feedback grace (20ms), including a late 6.9-second timer response.
    for (uint32_t hardwareDelay : std::array<uint32_t, 5>{0, 1, 1450, 3550, 6900}) {
        InputQualification input;
        for (uint32_t elapsed = 0; elapsed <= hardwareDelay + 1250; ++elapsed) {
            const auto r = input.update(true, elapsed >= hardwareDelay, true, start + elapsed);
            require(!r.fault, "Supported hardware delay produced a fault");
            require(r.ready == (elapsed == hardwareDelay + 1250), "Input ready before full quiet interval");
        }
        require(input.update(true, true, true, start + 1000000).ready,
                "Ready input expired during normal operation");
        const auto lost = input.update(true, false, true, start + 1000001);
        require(!lost.ready && !lost.fault, "Late ready loss did not start a fresh deadline");
        require(!input.update(true, true, true, start + 1000010).ready,
                "Ready loss skipped a new quiet interval");
        require(!input.update(true, true, true, start + 1001259).ready,
                "Recovery quiet interval ended early");
        require(input.update(true, true, true, start + 1001260).ready, "Recovery did not qualify");
    }
    InputQualification bounce;
    bounce.update(true, false, true, start);
    bounce.update(true, true, true, start + 100);
    require(!bounce.update(true, true, true, start + 1349).ready, "Quiet interval off by one");
    bounce.update(true, false, true, start + 1350);
    bounce.update(true, true, true, start + 1351);
    require(!bounce.update(true, true, true, start + 2600).ready,
            "Ready bounce did not restart quiet interval");
    require(bounce.update(true, true, true, start + 2601).ready, "Quiet interval after bounce failed");

    InputQualification timeout;
    timeout.update(true, false, true, start);
    require(!timeout.update(true, false, true, start + 9999).fault, "Timeout fired early");
    require(timeout.update(true, false, true, start + 10000).fault,
            "Missing hardware status never timed out");
    require(timeout.update(false, true, true, start + 10001).fault, "Input timeout was not latched");
    InputQualification chatter;
    for (uint32_t elapsed = 0; elapsed <= 10000; ++elapsed) {
        const auto r = chatter.update(true, (elapsed % 1000) != 0, true, start + elapsed);
        require(!r.ready, "Chattering input became ready");
        require(r.fault == (elapsed == 10000), "Chatter extended the total qualification deadline");
    }
    InputQualification calibration;
    calibration.update(true, true, true, start);
    require(calibration.update(true, true, true, start + 1250).ready, "Setup failed");
    require(!calibration.update(false, true, true, start + 1300).ready,
            "Calibration did not revoke qualification");
    require(!calibration.update(true, true, true, start + 1301).ready,
            "Stale high status skipped restart quiet interval");
    require(!calibration.update(true, true, true, start + 2550).ready, "Restart quiet ended early");
    require(calibration.update(true, true, true, start + 2551).ready, "Calibration restart never qualified");
    for (bool requested : {false, true}) {
        InputQualification bus;
        require(bus.update(requested, true, false, start).fault,
                "Missing rear/status bus did not latch a fault");
        require(bus.update(true, true, true, start + 1).fault, "Bus fault cleared without reset");
    }
}

// Exercise actual gain/input/rearm/feedback policies together, with a modeled
// hardware timer and edge-armed latch. This is not relay/contact bench evidence.
static void integration(uint32_t start) {
    ConnectionMode mode;
    InputQualification input;
    RearmDelay delay;
    RelayFeedback feedback;
    bool q = false, oldPermit = false, oldDrive = false;
    uint32_t timerSince = 0;
    bool first = false, afterManual = false, afterGain = false, afterFault = false;
    for (uint32_t t = 0; t <= 17000; ++t) {
        const uint32_t now = start + t;
        const bool manual = t >= 4500 && t < 4600;
        // Independent hardware PROCESS pole intentionally closes 15ms later.
        const bool process = !(t >= 4500 && t < 4615);
        const bool power = !(t >= 10000 && t < 10100);
        const auto gain = mode.update(t >= 6000, now);
        if (gain.driveSendReturn != oldDrive)
            timerSince = t;
        if (!power)
            timerSince = t + 1;
        oldDrive = gain.driveSendReturn;
        const bool hardwareReady = power && t >= timerSince + 2000;
        const auto qualified = input.update(power && gain.ready, hardwareReady, true, now);
        const bool desired = delay.update(qualified.ready && gain.ready && !manual && power, now);
        const auto relay = feedback.update(desired, q, now);
        const bool clear = power && process && hardwareReady;
        if (!clear)
            q = false;
        else if (relay.allowPermit && !oldPermit)
            q = true;
        const bool wet = clear && q && relay.allowPermit;
        oldPermit = relay.allowPermit;
        require(!qualified.fault && !relay.fault, "Normal sequencing produced a fault");
        if (t < 3600)
            require(!wet, "Startup selected wet before input quiet plus stable rearm");
        if (manual) {
            require(qualified.ready, "Manual bypass needlessly restarted input qualification");
            require(!wet, "Manual bypass left output wet");
        }
        if (t >= 4600 && t < 4950)
            require(!wet, "Manual release skipped stable rearm");
        if (t >= 6000 && t < 9628)
            require(!wet, "Gain transition selected wet before fresh input qualification");
        if (t >= 10000 && t < 13700)
            require(!wet, "Power recovery skipped input qualification");
        if (t == 4000)
            first = wet;
        if (t == 5000)
            afterManual = wet;
        if (t == 9700)
            afterGain = wet;
        if (t == 14000)
            afterFault = wet;
    }
    require(first && afterManual && afterGain && afterFault,
            "A healthy sequence never returned to wet output");
}

int main() {
    try {
        for (uint32_t start : std::array<uint32_t, 3>{0, 0xfffffff0u, 0xffff0000u}) {
            boundaries(start);
            integration(start);
        }
        std::cout << "Input qualification boundaries, bus faults, timeout/chatter, calibration, "
                     "manual bypass, actual gain/rearm/feedback integration and timer wrap passed\n";
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
