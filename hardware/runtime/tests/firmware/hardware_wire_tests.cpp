#include "hardware/firmware/WireFormat.h"
#include <bitset>
#include <iostream>
#include <stdexcept>

int main() {
    auto require = [](bool v, const char* message) {
        if (!v)
            throw std::runtime_error(message);
    };
    try {
        using namespace rmx::embedded;
        std::array<uint16_t, 96> led{};
        led[95] = 0x123;
        led[0] = 0xabc;
        const auto frame = packLedFrame(led);
        require(frame[0] == 0x12 && frame[1] == 0x30 && frame[142] == 0x0a && frame[143] == 0xbc,
                "LED chain bit order differs from wire contract");
        for (size_t i = 2; i < 142; ++i)
            require(frame[i] == 0, "LED data leaked into another channel");
        // Independent model of four cascaded 288-bit TLC5947 shift registers.
        // Exercise every output bit, including the middle chips, through the
        // actual transmitted byte stream; this is not a physical timing test.
        for (size_t selected = 0; selected < 96; ++selected) {
            for (size_t selectedBit = 0; selectedBit < 12; ++selectedBit) {
                led.fill(0);
                led[selected] = uint16_t(1u << selectedBit);
                std::array<std::bitset<288>, 4> registers{};
                for (const auto byte : packLedFrame(led)) {
                    for (int bit = 7; bit >= 0; --bit) {
                        bool incoming = (byte & (1u << bit)) != 0;
                        for (auto& chip : registers) {
                            const bool outgoing = chip[287];
                            chip <<= 1;
                            chip[0] = incoming;
                            incoming = outgoing;
                        }
                    }
                }
                for (size_t channel = 0; channel < 96; ++channel) {
                    uint16_t output = 0;
                    for (size_t bit = 0; bit < 12; ++bit)
                        if (registers[channel / 24][12 * (channel % 24) + bit])
                            output |= uint16_t(1u << bit);
                    require(output == led[channel], "TLC5947 cascade drove the wrong output bit");
                }
            }
        }
        require(angleDifference(304, 4000) == 400 && angleDifference(4000, 304) == -400, "Angle wrap failed");
        require(std::abs(leverPosition(104, 4000, 400) - .5f) < 1.e-6f, "Clockwise lever calibration failed");
        require(std::abs(leverPosition(104, 304, -400) - .5f) < 1.e-6f,
                "Counterclockwise lever calibration failed");
        require(leverPosition(104, 304, 0) == 0, "Invalid calibration was accepted");
        std::array<uint16_t, 8> touch{};
        require(!touchPosition(touch).active, "Untouched strip is active");
        touch[7] = 100;
        const auto right = touchPosition(touch);
        require(right.active && right.position > .875f && right.position <= 1,
                "Last electrode maps to wrong zone");
        touch = {};
        touch[0] = touch[1] = 100;
        const auto edge = touchPosition(touch);
        require(edge.active && std::abs(edge.position - .125f) < 1.e-6f,
                "Adjacent electrode centroid is wrong");
        std::cout
            << "LED serialization and all 1152 PWM bits through four cascaded drivers, lever calibration "
               "wrap/direction, and touch centroid checks passed\n";
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
