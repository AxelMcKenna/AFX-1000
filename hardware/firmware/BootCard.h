#pragma once
#include "rmx/storage/BootStorage.h"

namespace rmx::embedded {
enum class CardState : uint8_t { Missing, Ready, Partial, IoError, Timeout };
struct CardReport {
    CardState state{CardState::Missing};
    storage::Report assets;
    uint32_t elapsedMs{};
};
// Read-only, cold boot only, before StartAudio. No FAT access after this returns.
CardReport loadBootCard(SampleBank& bank, ParameterStore& parameters) noexcept;
} // namespace rmx::embedded
