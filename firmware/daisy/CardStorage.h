#pragma once
#include "daisy_seed.h"
#include "sys/fatfs.h"
#include "rmx/CardSamples.h"
#include "rmx/CardSettings.h"

namespace rmx::board {
enum class CardState : uint8_t { Absent,NoManifest,ManifestError,Loaded,Partial,IoError };
// Keep this object in AXI SRAM, not on the DTCM stack or in external SDRAM.
class alignas(32) CardStorage final : private CardFiles {
public:
    CardState load(SampleBank&,ParameterStore&) noexcept;
    CardReport report;
    CardError settingsError{CardError::NotRequested};
private:
    struct Reader final : SampleFile {
        alignas(32) FIL file{};
        alignas(32) std::array<std::byte,4096> bounce{};
        bool opened{};
        FRESULT openPath(const char*) noexcept;
        bool closeFile() noexcept;
        uint64_t size() const noexcept override;
        bool seek(uint32_t) noexcept override;
        size_t read(std::span<std::byte>) noexcept override;
    } reader;
    alignas(32) daisy::FatFSInterface filesystem;
    daisy::SdmmcHandler sdmmc;
    CardError loadSettings(ParameterStore&) noexcept;
    SampleFile* open(unsigned slot) noexcept override;
    bool close() noexcept override {return reader.closeFile();}
};
}
