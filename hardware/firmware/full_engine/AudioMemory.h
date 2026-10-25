#pragma once
#include "rmx/Dsp.h"
#include <memory_resource>
#include <new>

namespace rmx::embedded {
// Cold boot only: use the same resource and alignment as Sample::frames.
// A successful probe is not a reservation. The caller must prevent interleaved
// allocation, and still handle failure of the subsequent vector allocation.
inline bool probeAudioAllocation(std::pmr::memory_resource* resource, size_t bytes) noexcept {
    if (!resource || bytes < 4096)
        return false;
    try {
        auto* memory = resource->allocate(bytes, alignof(Stereo));
        resource->deallocate(memory, bytes, alignof(Stereo));
        return true;
    } catch (const std::bad_alloc&) {
        return false;
    }
}
} // namespace rmx::embedded
