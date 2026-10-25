#include "KernelTransport.h"
#include <bit>
#include <limits>

namespace rmx::sample_reader {
namespace {
#include "generated/kernel_data.inc"
static_assert(sizeof(Level) == 8452);
static_assert(std::numeric_limits<float>::is_iec559 && sizeof(float) == 4);
static_assert(std::endian::native == std::endian::little);

constexpr uint32_t crcByte(uint32_t crc, uint8_t byte) {
    crc ^= byte;
    for (unsigned bit = 0; bit < 8; ++bit)
        crc = (crc >> 1) ^ ((crc & 1) ? 0xedb88320u : 0u);
    return crc;
}
constexpr uint32_t crcWord(uint32_t crc, float value) {
    const auto word = std::bit_cast<uint32_t>(value);
    for (unsigned byte = 0; byte < 4; ++byte)
        crc = crcByte(crc, static_cast<uint8_t>(word >> (8 * byte)));
    return crc;
}
constexpr uint32_t crcLevel(uint32_t crc, const Level& level) {
    crc = crcWord(crc, level.cutoff);
    for (const auto& kernel : level.kernels)
        for (float value : kernel.weights) crc = crcWord(crc, value);
    return crc;
}
// Each compiler proves the payload was generated from its exact coefficients.
// Independent level expressions keep constexpr resource use bounded.
template<unsigned Index> struct VerifiedLevel {
    static constexpr auto reference = makeLevel(Index);
    static_assert((crcLevel(0xffffffffu, reference) ^ 0xffffffffu) == expectedLevelCrc[Index]);
    static constexpr bool value = true;
};
template<size_t... Index> consteval bool verify(std::index_sequence<Index...>) {
    return (VerifiedLevel<Index>::value && ...);
}
static_assert(verify(std::make_index_sequence<levels>{}));

#if defined(__arm__) || defined(__thumb__)
__attribute__((section(".sdram_bss"), aligned(32)))
#endif
std::array<Level, levels> restored;
bool ready{};
template<size_t... Index> consteval auto pointers(std::index_sequence<Index...>) {
    return std::array<const Level*, levels>{&restored[Index]...};
}
}
const std::array<const Level*, levels> table = pointers(std::make_index_sequence<levels>{});
std::span<const uint8_t> kernelPayload() noexcept { return packedKernels; }
bool decodeKernelTable(std::span<const uint8_t> input, std::span<Level> output) noexcept {
    if (output.size() != levels) return false;
    size_t position = 0;
    const auto word = [&](float& value) {
        if (input.size() - position < 4) return false;
        uint32_t bits = 0;
        for (unsigned i = 0; i < 4; ++i) bits |= uint32_t(input[position++]) << (8 * i);
        value = std::bit_cast<float>(bits);
        return true;
    };
    for (auto& level : output) {
        if (!word(level.cutoff)) return false;
        for (unsigned phase = 0; phase <= phases / 2; ++phase)
            for (auto& value : level.kernels[phase].weights)
                if (!word(value)) return false;
        for (unsigned phase = phases / 2 + 1; phase <= phases; ++phase) {
            for (unsigned tap = 0; tap < taps; ++tap) {
                uint32_t difference = 0;
                bool complete = false;
                for (unsigned byte = 0; byte < 5; ++byte) {
                    if (position == input.size()) return false;
                    const uint8_t next = input[position++];
                    if (byte == 4 && (next & 0xf0)) return false;
                    difference |= uint32_t(next & 0x7f) << (7 * byte);
                    if (!(next & 0x80)) { complete = true; break; }
                }
                if (!complete) return false;
                const auto mirror = std::bit_cast<uint32_t>(level.kernels[phases-phase].weights[taps-1-tap]);
                level.kernels[phase].weights[tap] = std::bit_cast<float>(mirror ^ difference);
            }
        }
    }
    if (position != input.size()) return false;
    uint32_t crc = 0xffffffffu;
    for (const auto& level : output) crc = crcLevel(crc, level);
    return (crc ^ 0xffffffffu) == expectedKernelCrc;
}
bool initializeTable() noexcept {
    if (ready) return true;
    ready = decodeKernelTable(packedKernels, restored);
    return ready;
}
bool tableReady() noexcept { return ready; }
}
