#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

namespace rmx::embedded {
// Chain order: MCU -> IC0 -> IC1 -> IC2 -> IC3. LED n is OUT(n%24) of IC(n/24).
inline std::array<uint8_t, 144> packLedFrame(const std::array<uint16_t, 96>& led) noexcept {
    std::array<uint8_t, 144> bytes{};
    for (size_t bit = 0; bit < 1152; ++bit)
        if ((led[95 - bit / 12] & 0xfff) & (1 << (11 - bit % 12)))
            bytes[bit / 8] |= uint8_t(1 << (7 - bit % 8));
    return bytes;
}
inline int16_t angleDifference(uint16_t value, uint16_t origin) noexcept {
    const int d = (static_cast<int>(value) - origin + 2048) & 4095;
    return static_cast<int16_t>(d - 2048);
}
inline float leverPosition(uint16_t raw, uint16_t home, int16_t travel) noexcept {
    if (std::abs(static_cast<int>(travel)) < 200 || std::abs(static_cast<int>(travel)) > 700)
        return 0;
    return std::clamp(static_cast<float>(angleDifference(raw, home)) / travel, 0.f, 1.f);
}
struct Touch {
    float position{};
    bool active{};
};
inline Touch touchPosition(const std::array<uint16_t, 8>& values) noexcept {
    // Prototype threshold at 10-bit acquisition. Tune against the actual cover.
    size_t strongest = 0;
    for (size_t i = 1; i < 8; ++i)
        if (values[i] > values[strongest])
            strongest = i;
    if (values[strongest] < 12)
        return {};
    float weight = 0, sum = 0;
    for (size_t i = 0; i < 8; ++i)
        if (i + 1 >= strongest && i <= strongest + 1 && values[i] > 8) {
            const float v = static_cast<float>(values[i] - 8);
            weight += v;
            sum += v * (static_cast<float>(i) + .5f);
        }
    return {sum / (weight * 8), true};
}
} // namespace rmx::embedded
