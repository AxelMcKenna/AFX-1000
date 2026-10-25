#include "hardware/firmware/RelayFeedback.h"
#include <iostream>
#include <stdexcept>

int main() {
    try {
        using rmx::embedded::RearmDelay;
        using rmx::embedded::RelayFeedback;
        auto require = [](bool v, const char* message) {
            if (!v)
                throw std::runtime_error(message);
        };
        RelayFeedback absent;
        require(!absent.update(false, false, 90).allowPermit, "Bypass requested an enable edge");
        auto r = absent.update(true, false, 100);
        require(r.allowPermit && !r.fault, "Initial permit edge was blocked");
        require(!absent.update(true, false, 119).fault, "Arming grace ended early");
        r = absent.update(true, false, 120);
        require(!r.allowPermit && r.fault, "Absent hardware feedback did not time out");

        RelayFeedback running;
        running.update(true, false, 0);
        require(running.update(true, true, 3).allowPermit, "Healthy hardware latch was rejected");
        r = running.update(true, false, 100);
        require(!r.allowPermit && !r.fault, "Latch loss must drop permit immediately with switch-pole grace");
        require(!running.update(true, false, 119).fault, "Fault diagnosis ignored pole timing allowance");
        require(running.update(true, false, 120).fault, "Persistent latch loss was not diagnosed");

        RelayFeedback manual;
        manual.update(true, true, 0);
        require(!manual.update(true, false, 10).allowPermit, "Manual hardware break did not drop permit");
        require(!manual.update(false, false, 15).fault, "Normal second-pole arrival latched a fault");
        r = manual.update(true, false, 100);
        require(r.allowPermit && !r.fault, "Leaving bypass did not allow a new arming edge");
        require(manual.update(true, true, 103).allowPermit, "Leaving bypass failed to arm");
        require(!manual.update(false, true, 110).allowPermit, "Software bypass left permit on");

        RelayFeedback pulse;
        pulse.update(true, true, 0);
        pulse.update(true, false, 20);
        r = pulse.update(true, true, 21);
        require(r.allowPermit && !r.fault, "Recovered feedback sample did not allow a fresh permit");

        RelayFeedback wrap;
        constexpr uint32_t start = 0xfffffff8u;
        wrap.update(true, false, start);
        require(!wrap.update(true, false, start + 19u).fault && wrap.update(true, false, start + 20u).fault,
                "Initial feedback timeout failed across timer wrap");
        RelayFeedback lostWrap;
        lostWrap.update(true, true, start - 1u);
        lostWrap.update(true, false, start);
        require(!lostWrap.update(true, false, start + 19u).fault &&
                    lostWrap.update(true, false, start + 20u).fault,
                "Lost feedback timeout failed across timer wrap");

        RearmDelay delay;
        require(!delay.update(true, 0) && !delay.update(true, 349) && delay.update(true, 350),
                "Initial eligibility did not wait the full stable interval");
        require(!delay.update(false, 500), "Manual bypass did not remove eligibility");
        require(!delay.update(true, 505) && !delay.update(true, 854) && delay.update(true, 855),
                "Manual bypass release could clock the latch before the other pole settles");
        delay.update(false, 900);
        delay.update(true, 905);
        delay.update(false, 910);
        require(!delay.update(true, 915) && !delay.update(true, 1264) && delay.update(true, 1265),
                "Bouncing eligibility did not restart the rearm interval");
        RearmDelay wrapDelay;
        require(!wrapDelay.update(true, start) && !wrapDelay.update(true, start + 349u) &&
                    wrapDelay.update(true, start + 350u),
                "Stable eligibility interval failed across timer wrap");

        // The actual policy classes together must not send a positive permit
        // during a late-closing PROCESS pole on the way out of manual bypass.
        RearmDelay interlockDelay;
        RelayFeedback interlockFeedback;
        for (uint32_t now = 0; now <= 400; ++now) {
            const bool desired = interlockDelay.update(now >= 10, now); // D0 leaves bypass at 10ms
            const bool hardwareClear = now >= 25;                       // PROCESS pole closes 15ms later
            static bool q = false, oldPermit = false;
            auto state = interlockFeedback.update(desired, q, now);
            if (!hardwareClear)
                q = false;
            else if (state.allowPermit && !oldPermit)
                q = true;
            oldPermit = state.allowPermit;
            require(!state.fault, "Normal manual pole delay produced a firmware fault");
            if (now < 360)
                require(!state.allowPermit, "Permit edge preceded stable manual release");
            if (now == 400)
                require(state.allowPermit && q, "Normal manual release never rearmed");
        }
        std::cout
            << "Hardware latch feedback, stable rearm, manual pole delay and clock-wrap checks passed\n";
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
