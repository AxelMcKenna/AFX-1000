#pragma once
#include "daisy_seed.h"
#include <atomic>

namespace rmx::embedded {
// One instance. SAI2B receives codec clocks/data; SAI2A transmits in sync.
// Raw DMA is used so StartDma errors reach the caller (AudioHandle::Start in
// the pinned SDK discards that result). DMA buffers are uncached D2 SRAM.
class ExternalAudio {
  public:
    using Callback = daisy::AudioHandle::AudioCallback;
    bool initialize(daisy::DaisySeed& hw);
    bool start(Callback callback, void (*onFault)());
    bool stop();
    void audible(bool value) {
        audible_.store(value, std::memory_order_relaxed);
    }
    void inputQualified(bool value) {
        inputQualified_.store(value, std::memory_order_relaxed);
    }
    uint32_t maxCallbackUs() const {
        return maxUs_.load(std::memory_order_relaxed);
    }
    uint32_t maxCopyUs() const {
        return maxCopyUs_.load(std::memory_order_relaxed);
    }
    bool hardwareError() const;
    static void notifyHardwareError();

  private:
    static ExternalAudio* instance_;
    static void dispatch(int32_t* input, int32_t* output, size_t samples);
    daisy::SaiHandle sai_;
    Callback callback_ = nullptr;
    void (*onFault_)() = nullptr;
    std::atomic<bool> audible_{};
    std::atomic<bool> inputQualified_{};
    std::atomic<uint32_t> maxUs_{};
    std::atomic<uint32_t> maxCopyUs_{};
};
} // namespace rmx::embedded
