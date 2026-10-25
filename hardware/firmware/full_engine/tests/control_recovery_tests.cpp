#include "../ControlRecovery.h"
#include "../ControlReset.h"
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {
using Gate = rmx::embedded::ControlRecovery;
void require(bool value, const char* message) {
    if (!value)
        throw std::runtime_error(message);
}
Gate::Frame frame(uint32_t now, uint32_t keys = 0, bool touched = false) {
    return {now, keys, true, true, true, true, touched, touched ? .6f : 0.f, true};
}
void bootAndHeldInputs() {
    Gate gate;
    constexpr uint32_t held = (uint32_t{1} << 2) | (uint32_t{1} << 11) | (uint32_t{1} << 17);
    auto boot = frame(100, held, true);
    boot.leverHome = false;
    auto result = gate.update(boot);
    require(result.healthy && result.reprime && result.clearGestures && !result.dispatch,
            "Boot frame must clear/reprime without dispatch");
    require(result.keys == 0 && result.blockedButtons == held && !result.touchActive &&
                !result.releaseAllowed,
            "Boot-held momentary input escaped suppression");
    for (uint32_t now = 101; now < 1000; ++now) {
        auto input = frame(now, held, true);
        input.leverHome = false;
        result = gate.update(input);
        require(result.healthy && result.dispatch && result.keys == 0 && !result.touchActive &&
                    !result.releaseAllowed,
                "Long boot hold became a live gesture");
        require(!result.clearGestures && !result.reprime, "Healthy hold repeatedly cleared state");
    }
    auto released = frame(1000);
    result = gate.update(released);
    require(result.blockedButtons == held && !result.touchActive && result.releaseAllowed,
            "First release sample wrongly removed button debounce");
    result = gate.update(frame(1004));
    require(result.blockedButtons == held, "Held buttons rearmed before 5 ms release");
    result = gate.update(frame(1005));
    require(result.blockedButtons == 0, "Stable released buttons failed to rearm");
    result = gate.update(frame(1006, held, true));
    require(result.keys == held && result.touchUpdated && result.touchActive,
            "Genuine post-release button/touch input was lost");
}
void faultAndTouchReadCache() {
    Gate gate;
    gate.update(frame(1));
    auto result = gate.update(frame(2, uint32_t{1} << 13, true));
    require(result.dispatch && result.touchActive && result.keys != 0, "Live gesture was not allowed");
    auto failure = frame(3);
    failure.touchValid = false;
    result = gate.update(failure);
    require(!result.healthy && !result.dispatch && result.clearGestures,
            "Touch failure did not suppress whole frame and clear gestures");
    for (uint32_t now = 4; now < 7; ++now) {
        auto between = frame(now);
        between.touchSampled = false;
        between.touchValid = true; // Unread placeholder must not repair cached failure.
        result = gate.update(between);
        require(!result.healthy && !result.dispatch && !result.clearGestures,
                "Unread touch placeholder repaired failure or repeated clear");
    }
    auto held = frame(7, uint32_t{1} << 13, true);
    result = gate.update(held);
    require(result.healthy && result.reprime && !result.dispatch && result.keys == 0 && !result.touchActive,
            "Recovered held inputs generated phantom actions");
    result = gate.update(frame(8, uint32_t{1} << 13, true));
    require(result.keys == 0 && !result.touchActive, "Held input escaped after re-prime");
    result = gate.update(frame(9));
    require(result.touchUpdated && !result.touchActive, "Fresh inactive touch failed to release block");
    result = gate.update(frame(14));
    require(result.blockedButtons == 0, "Recovered button release did not qualify");
    result = gate.update(frame(15, uint32_t{1} << 13, true));
    require(result.dispatch && result.keys != 0 && result.touchActive,
            "Post-recovery fresh action did not rearm");
}
void fullFrameValidityBeforeEvents() {
    Gate gate;
    gate.update(frame(100));
    auto invalidSelector = frame(101, (uint32_t{3} << 30) | (uint32_t{1} << 13), true);
    auto result = gate.update(invalidSelector);
    require(!result.healthy && !result.dispatch && result.clearGestures,
            "Pad/touch action dispatched before conflicting selector validation");
    result = gate.update(frame(102, uint32_t{1} << 13, true));
    require(result.reprime && result.keys == 0 && !result.touchActive,
            "Stale pressed state from invalid selector frame was replayed");
    auto invalidAngleOrRear = frame(103, uint32_t{1} << 14);
    invalidAngleOrRear.otherValid = false;
    result = gate.update(invalidAngleOrRear);
    require(!result.healthy && result.clearGestures, "Other-frame failure allowed an action");
    auto buttonReadFailure = frame(104);
    buttonReadFailure.buttonsValid = false;
    require(!gate.update(buttonReadFailure).healthy, "Failed button read was treated as all released");
    result = gate.update(frame(105, (uint32_t{1} << 29) | (uint32_t{1} << 31)));
    require(result.reprime && result.keys == ((uint32_t{1} << 29) | (uint32_t{1} << 31)),
            "Valid persistent selectors were suppressed as momentary controls");
}
void releaseChatterAndIndependentButtons() {
    Gate gate;
    constexpr uint32_t a = uint32_t{1} << 2, b = uint32_t{1} << 11;
    gate.update(frame(10, a | b));
    gate.update(frame(11, b));     // a starts release.
    gate.update(frame(15, a | b)); // Four milliseconds is chatter, not a release.
    auto result = gate.update(frame(16, b));
    require(result.blockedButtons == (a | b), "Brief release chatter rearmed a held input");
    result = gate.update(frame(20, b));
    require(result.blockedButtons == (a | b), "Restarted release timer lost its interval");
    result = gate.update(frame(21, b));
    require(result.blockedButtons == b, "Independent release of one button did not rearm it");
    result = gate.update(frame(22, a | b));
    require(result.keys == a && result.blockedButtons == b, "Held calibration chord modifier escaped");
}
void freshnessAndTimerWrap() {
    Gate gate;
    gate.update(frame(0xfffffff8));
    auto cached = frame(0x0000000c); // 20ms exactly across wrap.
    cached.touchSampled = false;
    auto result = gate.update(cached);
    require(result.healthy && result.dispatch, "Fresh touch cache expired at 20 ms/wrap boundary");
    cached.now = 0x0000000d;
    result = gate.update(cached);
    require(!result.healthy && result.clearGestures, "Stale touch remained healthy after 20 ms");
    cached.now = 0x0000000e;
    require(!gate.update(cached).healthy, "Stale cache repaired without a fresh touch read");
    result = gate.update(frame(0x0000000f, uint32_t{1} << 18));
    require(result.reprime && !result.dispatch && result.keys == 0,
            "Touch cache recovery replayed held Hold button");
    Gate releaseWrap;
    constexpr uint32_t key = uint32_t{1} << 17;
    releaseWrap.update(frame(0xfffffffc, key));
    releaseWrap.update(frame(0xfffffffd));
    result = releaseWrap.update(frame(1));
    require(result.blockedButtons == key, "Release debounce wrapped early");
    result = releaseWrap.update(frame(2));
    require(result.blockedButtons == 0, "Release debounce failed through uint32 wrap");
    result = releaseWrap.update(frame(3, key));
    require(result.keys == key, "Fresh key did not work after timer wrap");
}
void callbackProgressAndTickets() {
    rmx::embedded::CallbackProgress progress;
    require(progress.update(42, 0xfffffff8), "Initial callback observation failed");
    require(progress.update(42, 12), "Callback progress expired at20ms boundary");
    require(!progress.update(42, 13), "Stalled callback remained alive after20ms");
    require(progress.update(43, 14), "Resumed callback did not restore progress");
    require(progress.update(0xffffffff, 15) && progress.update(0, 16),
            "Callback block-count wrap was not progress");
    rmx::embedded::PriorityControlReset reset;
    auto initial = reset.begin(false);
    require(initial.reset && reset.pending(), "First callback did not reset boot state");
    reset.complete(initial);
    require(!reset.pending() && !reset.begin(false).reset,
            "Idle stale callbacks repeated acknowledged reset");
    reset.begin(true);
    auto stale = reset.begin(false);
    require(stale.reset && reset.takeStaleObservation() && !reset.takeStaleObservation(),
            "Fresh-to-stale notification was lost/repeated");
    reset.request();
    reset.complete(stale);
    require(reset.pending(), "New reset generation was acknowledged by older ticket");
    auto later = reset.begin(false);
    require(later.reset, "New reset request was lost");
    reset.complete(later);
    require(!reset.pending(), "New reset ticket did not acknowledge completion");
}
void everyMomentaryBit() {
    for (unsigned bit = 0; bit < 29; ++bit) {
        Gate gate;
        const uint32_t mask = uint32_t{1} << bit;
        auto result = gate.update(frame(100, mask));
        require(result.blockedButtons == mask && !(result.keys & mask),
                "Momentary bit escaped initial block");
        gate.update(frame(101));
        result = gate.update(frame(106));
        require(result.blockedButtons == 0 && result.keys == 0,
                "Momentary release generated a phantom press");
        result = gate.update(frame(107, mask));
        require(result.dispatch && result.keys == mask, "A momentary bit failed to rearm after release");
    }
}
void invalidTouchCoordinatesAndRepeatedFaults() {
    for (const float position :
         {std::numeric_limits<float>::quiet_NaN(), std::numeric_limits<float>::infinity(), -.1f, 1.1f}) {
        Gate gate;
        gate.update(frame(1));
        auto invalid = frame(2, uint32_t{1} << 13, true);
        invalid.touchPosition = position;
        auto result = gate.update(invalid);
        require(!result.healthy && result.clearGestures && !result.dispatch,
                "Invalid active touch coordinate allowed a button frame");
        auto unread = frame(3);
        unread.touchSampled = false;
        require(!gate.update(unread).healthy, "Bad touch coordinate was not cached as failure");
        auto recovered = frame(4, uint32_t{1} << 13, true);
        result = gate.update(recovered);
        require(result.reprime && !result.touchActive && result.keys == 0,
                "Fault/recovery chatter replayed an active input");
        recovered.now = 5;
        recovered.otherValid = false;
        result = gate.update(recovered);
        require(result.clearGestures && !result.healthy, "Second fault did not clear new episode");
        recovered.now = 6;
        require(!gate.update(recovered).clearGestures, "Same fault cleared repeatedly");
    }
}
} // namespace
int main() {
    try {
        bootAndHeldInputs();
        faultAndTouchReadCache();
        fullFrameValidityBeforeEvents();
        releaseChatterAndIndependentButtons();
        freshnessAndTimerWrap();
        invalidTouchCoordinatesAndRepeatedFaults();
        everyMomentaryBit();
        callbackProgressAndTickets();
        std::cout << "F06 recovery gate: boot/fault-held suppression, full-frame validation, cached touch "
                     "failure/staleness, 5 ms release chatter, independent controls, lever home and "
                     "uint32 timer-wrap tests passed\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
