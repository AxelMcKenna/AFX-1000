#pragma once
#include <array>
#include <atomic>
#include <cstddef>

namespace rmx {
// One producer (UI or the adapter's merged event source), one audio consumer.
template <class T, size_t Capacity> class SpscQueue {
    static_assert(Capacity >= 2 && (Capacity & (Capacity - 1)) == 0);

  public:
    bool push(const T& v) noexcept {
        const auto w = write.load(std::memory_order_relaxed), n = (w + 1) & (Capacity - 1);
        if (n == read.load(std::memory_order_acquire))
            return false;
        data[w] = v;
        write.store(n, std::memory_order_release);
        return true;
    }
    bool pop(T& v) noexcept {
        const auto r = read.load(std::memory_order_relaxed);
        if (r == write.load(std::memory_order_acquire))
            return false;
        v = data[r];
        read.store((r + 1) & (Capacity - 1), std::memory_order_release);
        return true;
    }

  private:
    std::array<T, Capacity> data{};
    alignas(64) std::atomic<size_t> write{};
    alignas(64) std::atomic<size_t> read{};
};
} // namespace rmx
