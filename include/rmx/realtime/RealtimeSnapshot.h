#pragma once
#include <array>
#include <atomic>
#include <memory>
#include <utility>

namespace rmx {
// One serialized publisher and one audio reader. Each owns a slot; the third
// slot transfers ownership through a single atomic exchange. New publications
// replace unread ones. Allocation and reclamation happen only on the publisher.
// The reader's reference remains valid until its next read(). Destroy only after
// both threads have stopped, and do not retain references across read() calls.
template <class T> class RealtimeSnapshot {
    static_assert(std::atomic<unsigned>::is_always_lock_free);
    static constexpr unsigned updated = 4, indexMask = 3;

  public:
    explicit RealtimeSnapshot(T initial) {
        slots[front] = std::make_unique<const T>(std::move(initial));
        latestValue = slots[front].get();
    }
    // Publisher only, including latest(). External serialization is required
    // when several control threads can publish.
    const T& latest() const noexcept {
        return *latestValue;
    }
    void publish(T value) {
        slots[back] = std::make_unique<const T>(std::move(value));
        latestValue = slots[back].get();
        back = middle.exchange(back | updated, std::memory_order_acq_rel) & indexMask;
        slots[back].reset();
    }
    // Reader only. Bounded work: no retry loop, reference counting or destruction.
    const T& read() noexcept {
        if (middle.load(std::memory_order_acquire) & updated)
            front = middle.exchange(front, std::memory_order_acq_rel) & indexMask;
        return *slots[front];
    }

  private:
    std::array<std::unique_ptr<const T>, 3> slots;
    alignas(64) std::atomic<unsigned> middle{1};
    unsigned front{0}, back{2};
    const T* latestValue{};
};
} // namespace rmx
