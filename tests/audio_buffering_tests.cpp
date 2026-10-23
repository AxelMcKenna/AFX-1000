#include "TestSupport.h"
#include "rmx/AudioBuffering.h"

int main() {
    return runTests([] {
        auto equal = rmx::inputBuffering(128, 48000, 128, 48000, 65536);
        require(equal && equal->initial == 258 && equal->maximum == 386,
                "Equal-rate route did not reserve two negotiated callbacks");
        auto unequal = rmx::inputBuffering(256, 96000, 512, 48000, 65536);
        require(unequal && unequal->initial == 2050 && unequal->step == 1024,
                "Buffering mixed input and output clock domains");
        auto large = rmx::inputBuffering(8192, 48000, 8192, 48000, 65536);
        require(large && large->initial > 8192, "Large device buffer was truncated below one callback");
        require(!rmx::inputBuffering(8192, 192000, 8192, 8000, 65536),
                "Impossible resampling route was accepted");
        require(!rmx::inputBuffering(0, 48000, 128, 48000, 65536) &&
                    !rmx::inputBuffering(128, NAN, 128, 48000, 65536),
                "Invalid device timing was accepted");
    });
}
