#pragma once
#include "CardSamples.h"
#include "Parameters.h"

namespace rmx {
// Project card profile, not the proprietary Pioneer SD/RSD representation.
inline constexpr size_t maximumCardSettingsBytes=16384;
struct CardUserSettings {
    std::array<float,parameterCount> values{};
    CardUserSettings() noexcept;
    // Install only advanced User settings, preserving physical/performance controls.
    void apply(ParameterStore&) const noexcept;
    bool operator==(const CardUserSettings&)const=default;
};
// Bounded, allocation-free, locale-independent parsing. Failures preserve result.
// Missing fields use defaults; unknown, duplicate or non-User fields are rejected.
CardError parseCardSettings(std::string_view,CardUserSettings&) noexcept;
CardError readCardSettings(SampleFile&,CardUserSettings&,std::span<std::byte> scratch) noexcept;
// On failure written is zero; output must be discarded. No null terminator.
CardError writeCardSettings(const CardUserSettings&,std::span<char>,size_t& written) noexcept;
}
