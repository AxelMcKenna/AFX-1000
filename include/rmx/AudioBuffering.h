#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <optional>

namespace rmx {
// All frame counts are in the input device's clock domain. Reserve two callback
// quanta initially; allow one extra after an underrun. Leave room for another
// complete capture callback so increasing latency cannot itself overflow the ring.
struct InputBuffering {
    uint32_t initial{}, maximum{}, step{};
};
inline std::optional<InputBuffering> inputBuffering(uint32_t inputFrames, double inputRate,
                                                    uint32_t outputFrames, double outputRate,
                                                    uint32_t capacity) noexcept {
    if (!inputFrames || !outputFrames || !std::isfinite(inputRate) || !std::isfinite(outputRate) ||
        inputRate < 8000 || inputRate > 192000 || outputRate < 8000 || outputRate > 192000 ||
        inputFrames + uint64_t{1} >= capacity)
        return {};
    const auto quantum = static_cast<uint64_t>(
        std::max(double(inputFrames), std::ceil(outputFrames * inputRate / outputRate)));
    const uint64_t available = capacity - inputFrames - 1;
    if (2 * quantum + 2 > available)
        return {};
    return InputBuffering{static_cast<uint32_t>(2 * quantum + 2),
                          static_cast<uint32_t>(std::min(3 * quantum + 2, available)),
                          static_cast<uint32_t>(quantum)};
}
} // namespace rmx
