#include "AudioArena.h"
#include "daisy.h"
#include <cstdlib>
#include <new>

namespace {
alignas(16) std::byte DSY_SDRAM_BSS audioMemory[48 * 1024 * 1024];
rmx::embedded::AudioArena arena;
bool ready{};
[[noreturn]] void exhausted() {
    for (;;) {
    }
} // External audio watchdog drops to NC dry bypass.
} // namespace
void initializeAudioMemory() {
    if (!arena.initialize(audioMemory, sizeof(audioMemory)))
        exhausted();
    ready = true;
}
// Only use before audio/interrupt users can allocate; paired with vector.reserve.
bool audioMemoryCanAllocate(size_t bytes) noexcept {
    return ready && bytes >= 4096 && arena.canAllocate(bytes);
}
size_t audioMemoryUsed() {
    return arena.usedBytes();
}
void* operator new(size_t bytes) {
    void* p = ready && bytes >= 4096 ? arena.allocate(bytes) : std::malloc(bytes ? bytes : 1);
    if (!p)
        exhausted();
    return p;
}
void operator delete(void* p) noexcept {
    if (!p)
        return;
    if (arena.owns(p)) {
        if (!arena.release(p))
            exhausted();
    } else
        std::free(p);
}
void* operator new[](size_t bytes) {
    return ::operator new(bytes);
}
void operator delete[](void* p) noexcept {
    ::operator delete(p);
}
void operator delete(void* p, size_t) noexcept {
    ::operator delete(p);
}
void operator delete[](void* p, size_t) noexcept {
    ::operator delete(p);
}
