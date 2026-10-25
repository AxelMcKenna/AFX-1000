#include "ExternalAudio.h"
#include "DmaHalf.h"
#include "Pcm32.h"
#include <algorithm>

namespace rmx::embedded {
namespace {
constexpr size_t frames = 128, bufferSamples = frames * 2 * 2;
int32_t DMA_BUFFER_MEM_SECTION __attribute__((aligned(32))) receive[bufferSamples];
int32_t DMA_BUFFER_MEM_SECTION __attribute__((aligned(32))) transmit[bufferSamples];
float inputFloat[2][frames], outputFloat[2][frames];
int32_t staged[frames * 2];
} // namespace
ExternalAudio* ExternalAudio::instance_ = nullptr;
bool ExternalAudio::initialize(daisy::DaisySeed& hw) {
    using namespace daisy;
    // Seed init configures its onboard SAI1 codec; it is not our audio path.
    if (hw.audio_handle.DeInit() != AudioHandle::Result::OK)
        return false;
    SaiHandle::Config cfg{};
    cfg.periph = SaiHandle::Config::Peripheral::SAI_2;
    cfg.sr = SaiHandle::Config::SampleRate::SAI_48KHZ;
    cfg.bit_depth = SaiHandle::Config::BitDepth::SAI_32BIT;
    cfg.a_sync = cfg.b_sync = SaiHandle::Config::Sync::SLAVE;
    cfg.a_dir = SaiHandle::Config::Direction::TRANSMIT;
    cfg.b_dir = SaiHandle::Config::Direction::RECEIVE;
    cfg.pin_config.mclk = Pin();
    cfg.pin_config.sb = seed::D25;
    cfg.pin_config.sa = seed::D26;
    cfg.pin_config.fs = seed::D27;
    cfg.pin_config.sck = seed::D28;
    return sai_.Init(cfg) == SaiHandle::Result::OK;
}
bool ExternalAudio::start(Callback callback, void (*onFault)()) {
    audible(false);
    inputQualified(false);
    callback_ = callback;
    onFault_ = onFault;
    instance_ = this;
    std::fill_n(receive, bufferSamples, 0);
    std::fill_n(transmit, bufferSamples, 0);
    if (sai_.StartDma(receive, transmit, bufferSamples, dispatch) == daisy::SaiHandle::Result::OK)
        return true;
    sai_.StopDma(); // A failed second start must not leave the first DMA running.
    if (onFault_)
        onFault_();
    return false;
}
bool ExternalAudio::stop() {
    audible(false);
    inputQualified(false);
    return sai_.StopDma() == daisy::SaiHandle::Result::OK;
}
bool ExternalAudio::hardwareError() const {
    constexpr uint32_t errors = SAI_xSR_OVRUDR | SAI_xSR_WCKCFG | SAI_xSR_AFSDET | SAI_xSR_LFSDET;
    return ((SAI2_Block_A->SR | SAI2_Block_B->SR) & errors) != 0;
}
void ExternalAudio::notifyHardwareError() {
    if (instance_) {
        instance_->audible(false);
        instance_->inputQualified(false);
        if (instance_->onFault_)
            instance_->onFault_();
    }
}
void ExternalAudio::dispatch(int32_t* input, int32_t* output, size_t samples) {
    auto& self = *instance_;
    const uint32_t start = daisy::System::GetUs();
    if (samples != frames * 2 || !self.callback_ || self.hardwareError()) {
        if (self.onFault_)
            self.onFault_();
        return;
    }
    // Keep startup/gain-settling ADC transients out of delay/roll histories,
    // in addition to holding the physical output dry and DAC data silent.
    decodeStereoPcm32(input, inputFloat[0], inputFloat[1], frames,
                      self.inputQualified_.load(std::memory_order_relaxed));
    const float* in[2] = {inputFloat[0], inputFloat[1]};
    float* out[2] = {outputFloat[0], outputFloat[1]};
    self.callback_(in, out, frames);
    bool valid = true;
    for (size_t i = 0; i < frames; ++i)
        valid = valid && std::isfinite(out[0][i]) && std::isfinite(out[1][i]);
    const bool audible = valid && self.audible_.load(std::memory_order_relaxed);
    for (size_t i = 0; i < frames; ++i) {
        staged[2 * i] = audible ? encodePcm32(out[0][i]) : 0;
        staged[2 * i + 1] = audible ? encodePcm32(out[1][i]) : 0;
    }
    // RX and TX start independently. Do not assume an RX half-complete event
    // alone proves the corresponding TX half is no longer in use. Stream3 is
    // SAI2A TX in the pinned SDK; a wrong/late phase fails closed.
    __DMB();
    if (!transmitHalfAvailable(static_cast<size_t>(output - transmit), DMA1_Stream3->NDTR) ||
        daisy::System::GetUs() - start > 2400) {
        notifyHardwareError();
        return;
    }
    const uint32_t copyStart = daisy::System::GetUs();
    std::copy_n(staged, samples, output);
    __DMB();
    const uint32_t copyUs = daisy::System::GetUs() - copyStart;
    if (copyUs > self.maxCopyUs_.load(std::memory_order_relaxed))
        self.maxCopyUs_.store(copyUs, std::memory_order_relaxed);
    const uint32_t elapsed = daisy::System::GetUs() - start;
    if (elapsed > self.maxUs_.load(std::memory_order_relaxed))
        self.maxUs_.store(elapsed, std::memory_order_relaxed);
    if (!valid || elapsed > 2400 || copyUs > 80)
        notifyHardwareError();
}
} // namespace rmx::embedded

extern "C" void HAL_SAI_ErrorCallback(SAI_HandleTypeDef* sai) {
    if (sai->Instance == SAI2_Block_A || sai->Instance == SAI2_Block_B)
        rmx::embedded::ExternalAudio::notifyHardwareError();
}
