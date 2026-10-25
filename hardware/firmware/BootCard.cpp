#include "BootCard.h"
#include "daisy_seed.h"
#include "sys/fatfs.h"
#include <cstring>
#include <new>

bool audioMemoryCanAllocate(size_t bytes) noexcept;

namespace rmx::embedded {
namespace {
struct alignas(32) DmaBuffers {
    daisy::FatFSInterface filesystem;
    alignas(32) FIL file;
    alignas(32) std::array<std::byte, 4096> bounce;
    // Isolate the complete allocation from unrelated CPU data/cache lines.
    alignas(32) std::array<std::byte, 64> guard;
};
static_assert(offsetof(FIL, buf) % 4 == 0 && offsetof(FATFS, win) % 4 == 0);
// BOOT_SRAM's ordinary .bss lives in DTCM, which SDMMC1 DMA cannot reach.
// The linker fragment puts this storage in AXI SRAM; initialize explicitly.
alignas(32) std::byte bootSdDmaStorage[sizeof(DmaBuffers)] __attribute__((section(".sdmmc_bss")));
constexpr uint32_t bootDeadlineMs = 8000;
class Card final : public storage::Files, private storage::File {
  public:
    explicit Card(DmaBuffers& dma) noexcept : data(dma), started(daisy::System::GetNow()) {}
    bool expired() const noexcept override {
        return static_cast<uint32_t>(daisy::System::GetNow() - started) >= bootDeadlineMs;
    }
    storage::File* open(storage::Kind kind, unsigned slot, storage::Error& error) noexcept override {
        if (opened || expired()) {
            error = expired() ? storage::Error::Timeout : storage::Error::Open;
            return nullptr;
        }
        const char* path = kind == storage::Kind::Preset ? "0:/RMX/BOOT.TXT" : "0:/RMX/USER.TXT";
        char sample[] = "0:/RMX/B1S1.WAV";
        if (kind == storage::Kind::Sample) {
            if (slot >= 16) {
                error = storage::Error::Open;
                return nullptr;
            }
            sample[8] = static_cast<char>('1' + slot / 4);
            sample[10] = static_cast<char>('1' + slot % 4);
            path = sample;
        }
        const auto status = f_open(&data.file, path, FA_READ);
        opened = status == FR_OK;
        error = opened                                         ? storage::Error::None
                : status == FR_NO_FILE || status == FR_NO_PATH ? storage::Error::Missing
                                                               : storage::Error::Open;
        return opened ? this : nullptr;
    }
    uint32_t size() const noexcept override {
        return opened ? f_size(&data.file) : 0;
    }
    bool seek(uint32_t offset) noexcept override {
        return opened && !expired() && offset <= f_size(&data.file) && f_lseek(&data.file, offset) == FR_OK &&
               f_tell(&data.file) == offset;
    }
    size_t read(std::span<std::byte> output) noexcept override {
        if (!opened || expired() || output.empty())
            return 0;
        // FatFs sends complete sectors directly to the supplied address. Use
        // an AXI bounce buffer, and align the file offset before direct DMA.
        const auto unaligned = f_tell(&data.file) & 3u;
        const auto count = static_cast<UINT>(
            std::min(output.size(), unaligned ? size_t(4 - unaligned) : data.bounce.size()));
        UINT received{};
        const auto result = f_read(&data.file, data.bounce.data(), count, &received);
        if (result != FR_OK || received > count || expired())
            return 0;
        std::memcpy(output.data(), data.bounce.data(), received);
        return received;
    }
    bool close() noexcept override {
        if (!opened)
            return true;
        opened = false;
        return f_close(&data.file) == FR_OK;
    }
    bool canAllocate(size_t bytes) const noexcept override {
        return audioMemoryCanAllocate(bytes);
    }
    uint32_t elapsed() const noexcept {
        return daisy::System::GetNow() - started;
    }

  private:
    DmaBuffers& data;
    const uint32_t started;
    bool opened{};
};
} // namespace
CardReport loadBootCard(SampleBank& bank, ParameterStore& parameters) noexcept {
    std::memset(bootSdDmaStorage, 0, sizeof(bootSdDmaStorage));
    auto& buffers = *new (bootSdDmaStorage) DmaBuffers;
    Card card(buffers);
    CardReport report;
    daisy::SdmmcHandler sdmmc;
    daisy::SdmmcHandler::Config config;
    config.Defaults();
    config.speed = daisy::SdmmcHandler::Speed::STANDARD;
    if (sdmmc.Init(config) != daisy::SdmmcHandler::Result::OK ||
        buffers.filesystem.Init(daisy::FatFSInterface::Config::MEDIA_SD) != daisy::FatFSInterface::OK) {
        report.state = CardState::IoError;
        report.elapsedMs = card.elapsed();
        return report;
    }
    const auto mounted = f_mount(&buffers.filesystem.GetSDFileSystem(), buffers.filesystem.GetSDPath(), 1);
    if (mounted == FR_OK && !card.expired()) {
        report.assets = storage::load(card, bank, parameters);
        bool failed =
            report.assets.preset != storage::Error::None && report.assets.preset != storage::Error::Missing;
        failed |= report.assets.user != storage::Error::None && report.assets.user != storage::Error::Missing;
        for (auto error : report.assets.samples)
            failed |= error != storage::Error::None && error != storage::Error::Missing;
        report.state = report.assets.timedOut ? CardState::Timeout
                       : failed               ? CardState::Partial
                                              : CardState::Ready;
    } else {
        report.state = card.expired()            ? CardState::Timeout
                       : mounted == FR_NOT_READY ? CardState::Missing
                                                 : CardState::IoError;
    }
    const bool closed = card.close();
    const auto unmounted = f_mount(nullptr, buffers.filesystem.GetSDPath(), 0);
    const auto unlinked = buffers.filesystem.DeInit();
    if (!closed || unmounted != FR_OK || unlinked != daisy::FatFSInterface::OK)
        report.state = CardState::IoError;
    report.elapsedMs = card.elapsed();
    return report;
}
} // namespace rmx::embedded
