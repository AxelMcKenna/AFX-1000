#pragma once
#include <cstddef>
#include <cstdint>

namespace rmx::embedded {
// TX DMA has 512 stereo-interleaved words in two 256-word halves. NDTR counts
// down. Write only the half DMA has consumed, leaving >=16 words before reuse.
// That reserve is ~166us at 48kHz; the real copy time still needs measurement.
inline bool transmitHalfAvailable(size_t offset, uint32_t remaining) {
    if (remaining == 0 || remaining > 512)
        return false;
    if (offset == 0)
        return remaining >= 16 && remaining <= 256;
    if (offset == 256)
        return remaining >= 272;
    return false;
}
} // namespace rmx::embedded
