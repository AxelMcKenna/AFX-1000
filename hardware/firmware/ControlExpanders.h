#pragma once
#include <cstdint>
#include <initializer_list>

namespace rmx::embedded {
// MCP23017 DS20001952D: GPA7/GPB7 are output-only. Front inputs use
// 0x20 A0..A6/B0..B6, 0x21 A0..A6/B0..B6, then 0x22 B0..B3.
// 0x22 A0..A3 remain dedicated to the external profile's rear/status inputs.
// The shared hardware reset must precede configuration (BANK=0, SEQOP=0).
template <class Write, class Read> bool configureControlExpanders(Write&& write, Read&& read, bool external) {
    for (uint8_t address : {0x20, 0x21, 0x22}) {
        const uint8_t directionA = address == 0x22 ? (external ? 0x0f : 0x00) : 0x7f;
        const uint8_t directionB = address == 0x22 ? 0x0f : 0x7f;
        // Status inputs A2/A3 require physical pull-downs, never pull-ups.
        const uint8_t pullA = address == 0x22 ? (external ? 0x03 : 0x00) : 0x7f;
        const uint8_t pullB = directionB;
        // Set unused outputs low before enabling their output drivers.
        if (!write(address, 0x14, {0, 0}) || !write(address, 0x00, {directionA, directionB}) ||
            !write(address, 0x0c, {pullA, pullB}))
            return false;
        uint8_t actual[2]{};
        if (!read(address, 0x00, actual, 2) || actual[0] != directionA || actual[1] != directionB)
            return false;
        if (!read(address, 0x0c, actual, 2) || actual[0] != pullA || actual[1] != pullB)
            return false;
        if (!read(address, 0x14, actual, 2) || actual[0] != 0 || actual[1] != 0)
            return false;
    }
    return true;
}

template <class Read> bool readControlButtons(Read&& read, uint32_t& pressed) {
    uint8_t first[2]{}, second[2]{}, tail{};
    if (!read(0x20, 0x12, first, 2) || !read(0x21, 0x12, second, 2) || !read(0x22, 0x13, &tail, 1))
        return false;
    const auto fourteen = [](const uint8_t* ports) {
        return uint32_t(~ports[0] & 0x7f) | (uint32_t(~ports[1] & 0x7f) << 7);
    };
    // Publish only a complete frame; a failed third read must not mix frames.
    pressed = fourteen(first) | (fourteen(second) << 14) | (uint32_t(~tail & 0x0f) << 28);
    return true;
}
} // namespace rmx::embedded
