#include "../hardware/firmware/ControlExpanders.h"
#include <array>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {
void require(bool value, const char* message) {
    if (!value)
        throw std::runtime_error(message);
}
struct Bus {
    std::array<std::array<uint8_t, 0x16>, 3> registers{};
    unsigned calls{}, failAt{}, corruptAt{};
    std::vector<std::array<unsigned, 4>> transfers;
    bool write(uint8_t address, uint8_t reg, std::initializer_list<uint8_t> bytes) {
        transfers.push_back({1, address, reg, unsigned(bytes.size())});
        if (++calls == failAt)
            return false;
        for (uint8_t value : bytes)
            registers.at(address - 0x20).at(reg++) = value;
        return true;
    }
    bool read(uint8_t address, uint8_t reg, uint8_t* bytes, uint16_t count) {
        transfers.push_back({0, address, reg, count});
        if (++calls == failAt)
            return false;
        for (unsigned i = 0; i < count; ++i)
            bytes[i] = registers.at(address - 0x20).at(reg + i);
        if (calls == corruptAt)
            bytes[count - 1] ^= 1;
        return true;
    }
    bool configure(bool external) {
        return rmx::embedded::configureControlExpanders(
            [this](uint8_t a, uint8_t r, std::initializer_list<uint8_t> b) { return write(a, r, b); },
            [this](uint8_t a, uint8_t r, uint8_t* b, uint16_t n) { return read(a, r, b, n); }, external);
    }
    bool buttons(uint32_t& result) {
        return rmx::embedded::readControlButtons(
            [this](uint8_t a, uint8_t r, uint8_t* b, uint16_t n) { return read(a, r, b, n); }, result);
    }
};
// Independent physical fixtures: {address offset, port offset, bit} in the
// established logical order, including settings and both release endpoints.
constexpr std::array<std::array<unsigned, 3>, 32> pins{
    {{0, 0, 0}, {0, 0, 1}, {0, 0, 2}, {0, 0, 3}, {0, 0, 4}, {0, 0, 5}, {0, 0, 6}, {0, 1, 0},
     {0, 1, 1}, {0, 1, 2}, {0, 1, 3}, {0, 1, 4}, {0, 1, 5}, {0, 1, 6}, {1, 0, 0}, {1, 0, 1},
     {1, 0, 2}, {1, 0, 3}, {1, 0, 4}, {1, 0, 5}, {1, 0, 6}, {1, 1, 0}, {1, 1, 1}, {1, 1, 2},
     {1, 1, 3}, {1, 1, 4}, {1, 1, 5}, {1, 1, 6}, {2, 1, 0}, {2, 1, 1}, {2, 1, 2}, {2, 1, 3}}};
void frame(Bus& bus, uint32_t pressed) {
    // Output-only/unused pins read low. They must never become button presses.
    for (auto& device : bus.registers)
        device[0x12] = device[0x13] = 0;
    for (unsigned i = 0; i < pins.size(); ++i) {
        auto p = pins[i];
        if (!(pressed & (uint32_t(1) << i)))
            bus.registers[p[0]][0x12 + p[1]] |= uint8_t(1 << p[2]);
    }
}
} // namespace

int main() {
    try {
        unsigned injected = 0;
        for (bool external : {false, true}) {
            Bus normal;
            require(normal.configure(external), "Expander setup failed");
            require(normal.calls == 18, "Unexpected configuration transaction count");
            for (unsigned device = 0; device < 3; ++device) {
                const auto& r = normal.registers[device];
                const unsigned a = device < 2 ? 0x7f : (external ? 0x0f : 0);
                const unsigned b = device < 2 ? 0x7f : 0x0f;
                require(r[0] == a && r[1] == b, "Invalid input pin direction");
                require(r[0x0c] == (device < 2 ? 0x7f : (external ? 3 : 0)) && r[0x0d] == b,
                        "Unsafe pull-up configuration");
                require(!(r[0] & 0x80) && !(r[1] & 0x80), "Output-only pin configured as input");
                require(r[0x14] == 0 && r[0x15] == 0, "Unused output latch is not low");
                const auto first = normal.transfers[device * 6];
                require(first == std::array<unsigned, 4>{1, 0x20 + device, 0x14, 2},
                        "Outputs enabled before latches initialized");
            }
            require(!(normal.registers[2][0x0c] & 0x0c), "Qualification status has an internal pull-up");
            for (unsigned failure = 1; failure <= 18; ++failure) {
                Bus faulty;
                faulty.failAt = failure;
                require(!faulty.configure(external), "Setup bus failure accepted");
                require(faulty.calls == failure, "Setup continued after failure");
                ++injected;
            }
            for (unsigned chip = 0; chip < 3; ++chip)
                for (unsigned read = 4; read <= 6; ++read) {
                    Bus faulty;
                    faulty.corruptAt = chip * 6 + read;
                    require(!faulty.configure(external), "Setup readback mismatch accepted");
                    ++injected;
                }
        }
        Bus bus;
        uint32_t actual = 0xdeadbeef;
        frame(bus, 0);
        require(bus.buttons(actual) && actual == 0, "Unused outputs create phantom presses");
        const std::vector<std::array<unsigned, 4>> expected{
            {0, 0x20, 0x12, 2}, {0, 0x21, 0x12, 2}, {0, 0x22, 0x13, 1}};
        require(bus.transfers == expected, "Input scan reads the wrong physical registers");
        for (unsigned bit = 0; bit < 32; ++bit) {
            const uint32_t one = uint32_t(1) << bit;
            frame(bus, one);
            require(bus.buttons(actual) && actual == one,
                    "A physical input maps to the wrong logical control");
            frame(bus, ~one);
            require(bus.buttons(actual) && actual == ~one, "Concurrent presses lose a logical control");
        }
        // Deterministic mixed frames, with every unused pin and rear status
        // changing independently. Only physical front inputs may affect output.
        uint32_t random = 0x4a93c710;
        for (unsigned i = 0; i < 4096; ++i) {
            random ^= random << 13;
            random ^= random >> 17;
            random ^= random << 5;
            frame(bus, random);
            for (unsigned c = 0; c < 2; ++c)
                for (unsigned port = 0; port < 2; ++port)
                    bus.registers[c][0x12 + port] |= uint8_t(((i >> (c * 2 + port)) & 1) << 7);
            bus.registers[2][0x12] = uint8_t(i);
            bus.registers[2][0x13] |= uint8_t(i & 0xf0);
            require(bus.buttons(actual) && actual == random,
                    "Rear/status/unused pins interfere with front inputs");
        }
        for (unsigned failure = 1; failure <= 3; ++failure) {
            Bus faulty;
            frame(faulty, 0xfedcba98);
            faulty.failAt = failure;
            actual = 0x12345678;
            require(!faulty.buttons(actual) && actual == 0x12345678, "Incomplete frame was published");
            require(faulty.calls == failure, "Scan continued after bus failure");
            ++injected;
        }
        std::cout << "Control expanders: 32 physical inputs, 4096 mixed frames, output-only/rear isolation, "
                     "both profiles and "
                  << injected << " injected bus/readback failures passed\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
