#pragma once
#include <algorithm>
#include <array>

namespace rmx::drums {
// Numeric factory customization calibration; raw gain choice3 is0dB.
inline float profileGain(unsigned raw) noexcept {
    constexpr std::array<float,7> values{1.4125375747680664f,1.258925437927246f,1.1220184564590454f,
        1.f,.8912509083747864f,.7943282127380371f,.7079457640647888f};
    return values[std::min(raw,6u)];
}
}
