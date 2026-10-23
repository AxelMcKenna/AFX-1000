#include "hardware/firmware/AudioArena.h"
#include <iostream>
#include <stdexcept>

int main() {
    auto require = [](bool v, const char* text) {
        if (!v)
            throw std::runtime_error(text);
    };
    try {
        alignas(16) std::array<std::byte, 8192> memory;
        rmx::embedded::AudioArena arena;
        require(!arena.initialize(memory.data() + 1, memory.size() - 1), "Misaligned arena accepted");
        require(arena.initialize(memory.data(), memory.size()), "Arena initialization failed");
        auto* a = static_cast<std::byte*>(arena.allocate(1023));
        auto* b = static_cast<std::byte*>(arena.allocate(2048));
        auto* c = static_cast<std::byte*>(arena.allocate(3072));
        require(a && b && c && reinterpret_cast<uintptr_t>(a) % 16 == 0, "Allocation/alignment failed");
        for (size_t i = 0; i < 1023; ++i)
            a[i] = std::byte{0x42};
        for (size_t i = 0; i < 3072; ++i)
            c[i] = std::byte{0x7a};
        require(arena.release(b), "Free failed");
        auto* d = static_cast<std::byte*>(arena.allocate(2000));
        require(d == b, "Fragment was not reused");
        for (size_t i = 0; i < 1023; ++i)
            require(a[i] == std::byte{0x42}, "Neighbor payload was overwritten");
        for (size_t i = 0; i < 3072; ++i)
            require(c[i] == std::byte{0x7a}, "Neighbor payload was overwritten");
        require(!arena.release(a + 1), "Interior pointer accepted");
        require(arena.release(c) && arena.release(a) && arena.release(d), "Out-of-order frees failed");
        require(arena.usedBytes() == 0 && !arena.release(a), "Double free/accounting failed");
        require(arena.allocate(memory.size()) == memory.data(), "Adjacent free blocks did not coalesce");
        require(!arena.allocate(16), "Exhausted arena accepted allocation");
        require(arena.peakBytes() == memory.size(), "Peak measurement is wrong");
        std::cout << "Audio arena alignment, reuse, payload preservation and exhaustion checks passed\n";
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
