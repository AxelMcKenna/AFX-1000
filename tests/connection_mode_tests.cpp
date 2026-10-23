#include "../hardware/firmware/ConnectionMode.h"
#include <iostream>
#include <stdexcept>

int main() {
    try {
        using rmx::embedded::ConnectionMode;
        auto require = [](bool value, const char* message) {
            if (!value)
                throw std::runtime_error(message);
        };
        ConnectionMode mode;
        auto state = mode.update(true, 0);
        require(!state.ready && !state.driveSendReturn, "Startup engaged gain before dry bypass");
        state = mode.update(true, 8);
        require(!state.ready && !state.driveSendReturn, "Debounce skipped dry wait");
        state = mode.update(true, 27);
        require(!state.ready && !state.driveSendReturn, "Coils changed before bypass release allowance");
        state = mode.update(true, 28);
        require(!state.ready && state.driveSendReturn, "Gain driver did not switch while bypassed");
        state = mode.update(true, 57);
        require(!state.ready, "Processing resumed before gain relays settled");
        require(mode.update(true, 58).ready, "Startup gain did not become ready");
        state = mode.update(false, 100);
        require(!state.ready && state.driveSendReturn, "Mode edge did not request immediate bypass");
        mode.update(false, 108);
        // Contact bounce during the dry wait restarts the sequence.
        state = mode.update(true, 120);
        require(!state.ready && state.driveSendReturn, "Bounce permitted processing");
        mode.update(false, 123);
        mode.update(false, 131);
        require(mode.update(false, 150).driveSendReturn, "Bounce shortened dry allowance");
        state = mode.update(false, 151);
        require(!state.ready && !state.driveSendReturn, "Master gain switch was not sequenced");
        require(!mode.update(false, 180).ready && mode.update(false, 181).ready,
                "Master settle interval is wrong");

        // Delayed foreground polling must not catch up multiple phases at once.
        ConnectionMode delayed;
        delayed.update(true, 0);
        delayed.update(true, 1000);
        require(!delayed.update(true, 1001).driveSendReturn, "Delayed poll skipped dry wait");
        state = delayed.update(true, 1020);
        require(state.driveSendReturn && !state.ready, "Delayed poll skipped settling");
        require(delayed.update(true, 1050).ready, "Delayed sequence never completed");

        ConnectionMode wrapped;
        constexpr uint32_t start = 0xfffffff0u;
        wrapped.update(true, start);
        wrapped.update(true, start + 8u);
        state = wrapped.update(true, start + 28u);
        require(state.driveSendReturn && !state.ready, "Clock wrap changed dry wait");
        require(wrapped.update(true, start + 58u).ready, "Clock wrap changed settle interval");
        std::cout << "Connection gain sequencing, bounce, delayed polling and clock wrap passed\n";
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
