#pragma once
#include "ControlRecovery.h"
#include <atomic>
#include <cstdint>

namespace rmx::embedded {
// One callback consumer; the foreground and callback may request a reset.
// Tickets prevent a request arriving during DSP from being acknowledged early.
class PriorityControlReset {
  public:
    struct Ticket {
        uint32_t generation{};
        bool reset{};
    };
    static_assert(std::atomic<uint32_t>::is_always_lock_free);
    void request() noexcept {
        requested_.fetch_add(1, std::memory_order_acq_rel);
    }
    void observeFreshness(bool fresh) noexcept {
        if (!fresh && previouslyFresh_) {
            request();
            staleObserved_.store(true, std::memory_order_release);
        }
        previouslyFresh_ = fresh;
    }
    Ticket begin(bool fresh) noexcept {
        observeFreshness(fresh);
        const uint32_t generation = requested_.load(std::memory_order_acquire);
        return {generation, generation != completed_.load(std::memory_order_acquire)};
    }
    void complete(Ticket ticket) noexcept {
        if (ticket.reset)
            completed_.store(ticket.generation, std::memory_order_release);
    }
    bool pending() const noexcept {
        const auto completed = completed_.load(std::memory_order_acquire);
        return completed != requested_.load(std::memory_order_acquire);
    }
    bool takeStaleObservation() noexcept {
        return staleObserved_.exchange(false, std::memory_order_acq_rel);
    }
    uint32_t generation() const noexcept {
        return requested_.load(std::memory_order_acquire);
    }

  private:
    // The first callback resets pre-audio foreground state as well.
    std::atomic<uint32_t> requested_{1}, completed_{};
    std::atomic<bool> staleObserved_{};
    bool previouslyFresh_{}; // Callback-owned only.
};
// Foreground progress check; does not replace the independent audio watchdog.
class CallbackProgress {
  public:
    bool update(uint32_t blocks, uint32_t now) noexcept {
        if (!initialized_ || blocks != previousBlocks_) {
            initialized_ = true;
            previousBlocks_ = blocks;
            progressedAt_ = now;
        }
        return static_cast<uint32_t>(now - progressedAt_) <= ControlRecovery::touchFreshMs;
    }

  private:
    uint32_t previousBlocks_{}, progressedAt_{};
    bool initialized_{};
};
} // namespace rmx::embedded
