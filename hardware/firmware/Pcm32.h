#pragma once
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>

namespace rmx::embedded {
inline float decodePcm32(int32_t value) {
    return static_cast<float>(value) * 0x1p-31f;
}
inline void decodeStereoPcm32(const int32_t* input, float* left, float* right, size_t frames,
                              bool qualified) {
    for (size_t i = 0; i < frames; ++i) {
        left[i] = qualified ? decodePcm32(input[2 * i]) : 0.f;
        right[i] = qualified ? decodePcm32(input[2 * i + 1]) : 0.f;
    }
}
inline int32_t encodePcm32(float value) {
    if (!std::isfinite(value))
        return 0;
    if (value >= 1.f)
        return std::numeric_limits<int32_t>::max();
    if (value <= -1.f)
        return std::numeric_limits<int32_t>::min();
    return static_cast<int32_t>(value * 0x1p31f);
}
} // namespace rmx::embedded
