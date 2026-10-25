#pragma once
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>

namespace rmx::embedded {
// Foreground/startup allocator for the engine's large vector buffers. Never call
// from the audio callback. Metadata stays in internal SRAM; payload lives in SDRAM.
class AudioArena {
  public:
    bool initialize(void* memory, size_t bytes) noexcept {
        if (!memory || reinterpret_cast<uintptr_t>(memory) % 16 ||
            bytes > std::numeric_limits<uint32_t>::max())
            return false;
        base = static_cast<std::byte*>(memory);
        capacity = static_cast<uint32_t>(bytes & ~size_t(15));
        segments = {};
        segments[0] = {0, capacity, true, false};
        live = peak = 0;
        return capacity != 0;
    }
    void* allocate(size_t bytes) noexcept {
        if (bytes == 0)
            bytes = 1;
        if (!base || bytes > capacity || bytes > std::numeric_limits<uint32_t>::max() - 15)
            return nullptr;
        const uint32_t aligned = static_cast<uint32_t>((bytes + 15) & ~size_t(15));
        size_t selected = segments.size();
        for (size_t i = 0; i < segments.size(); ++i) {
            const auto& s = segments[i];
            if (s.active && !s.used && s.bytes >= aligned &&
                (selected == segments.size() || s.bytes < segments[selected].bytes))
                selected = i;
        }
        if (selected == segments.size())
            return nullptr;
        auto& s = segments[selected];
        if (s.bytes > aligned)
            for (auto& spare : segments)
                if (!spare.active) {
                    spare = {s.offset + aligned, s.bytes - aligned, true, false};
                    s.bytes = aligned;
                    break;
                }
        s.used = true;
        live += s.bytes;
        if (live > peak)
            peak = live;
        return base + s.offset;
    }
    bool owns(const void* p) const noexcept {
        const auto value = reinterpret_cast<uintptr_t>(p), begin = reinterpret_cast<uintptr_t>(base);
        return base && value >= begin && value - begin < capacity;
    }
    bool release(void* p) noexcept {
        if (!owns(p))
            return false;
        const auto offset = static_cast<uint32_t>(static_cast<std::byte*>(p) - base);
        for (auto& s : segments)
            if (s.active && s.used && s.offset == offset) {
                s.used = false;
                live -= s.bytes;
                // Coalesce to make repeated stopped-audio bank replacement reusable.
                bool merged;
                do {
                    merged = false;
                    for (size_t i = 0; i < segments.size() && !merged; ++i)
                        if (segments[i].active && !segments[i].used)
                            for (size_t j = i + 1; j < segments.size(); ++j)
                                if (segments[j].active && !segments[j].used) {
                                    auto& a = segments[i];
                                    auto& b = segments[j];
                                    if (a.offset + a.bytes == b.offset || b.offset + b.bytes == a.offset) {
                                        a.offset = a.offset < b.offset ? a.offset : b.offset;
                                        a.bytes += b.bytes;
                                        b.active = false;
                                        merged = true;
                                        break;
                                    }
                                }
                } while (merged);
                return true;
            }
        return false;
    }
    bool canAllocate(size_t bytes) const noexcept {
        if (!base || bytes > std::numeric_limits<uint32_t>::max() - 15)
            return false;
        const auto aligned = static_cast<uint32_t>((std::max<size_t>(bytes, 1) + 15) & ~size_t(15));
        for (const auto& segment : segments)
            if (segment.active && !segment.used && segment.bytes >= aligned)
                return true;
        return false;
    }
    size_t usedBytes() const noexcept {
        return live;
    }
    size_t peakBytes() const noexcept {
        return peak;
    }

  private:
    struct Segment {
        uint32_t offset{}, bytes{};
        bool active{}, used{};
    };
    std::array<Segment, 128> segments{};
    std::byte* base{};
    uint32_t capacity{};
    size_t live{}, peak{};
};
} // namespace rmx::embedded
