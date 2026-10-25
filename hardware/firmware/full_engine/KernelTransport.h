#pragma once
#include "rmx/SampleReader.h"
#include <cstdint>
#include <span>

namespace rmx::sample_reader {
// Decode into unpublished caller storage. Failure never publishes a table.
bool decodeKernelTable(std::span<const uint8_t> input, std::span<Level> output) noexcept;
std::span<const uint8_t> kernelPayload() noexcept;
}
