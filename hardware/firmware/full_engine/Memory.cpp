#include "daisy.h"
#include "AudioMemory.h"
#include "rmx/FixedArena.h"
#include <memory_resource>
#include <optional>

namespace {
alignas(std::max_align_t) std::byte DSY_SDRAM_BSS audioMemory[60u * 1024 * 1024];
std::optional<rmx::FixedArena> arena;
}
void initializeAudioMemory() {
    arena.emplace(audioMemory, sizeof(audioMemory));
    std::pmr::set_default_resource(&*arena);
}
// Cold boot only. Probe the same resource and alignment used by the next reserve;
// no audio or other PMR allocator user is running between the probe and reserve.
bool audioMemoryCanAllocate(size_t bytes) noexcept {
    return rmx::embedded::probeAudioAllocation(arena ? &*arena : nullptr, bytes);
}
size_t audioMemoryUsed() { return arena ? arena->used() : 0; }
