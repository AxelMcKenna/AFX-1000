#include "rmx/storage/BootStorage.h"
#include <bit>
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <string_view>

namespace rmx::storage {
namespace {
bool exact(File& file, std::span<std::byte> bytes) noexcept {
    while (!bytes.empty()) {
        const auto count = file.read(bytes);
        if (!count || count > bytes.size())
            return false;
        bytes = bytes.subspan(count);
    }
    return true;
}
uint16_t u16(const std::byte* b) noexcept {
    return uint16_t(std::to_integer<uint8_t>(b[0]) | (std::to_integer<uint8_t>(b[1]) << 8));
}
uint32_t u32(const std::byte* b) noexcept {
    return uint32_t(std::to_integer<uint8_t>(b[0])) | (uint32_t(std::to_integer<uint8_t>(b[1])) << 8) |
           (uint32_t(std::to_integer<uint8_t>(b[2])) << 16) |
           (uint32_t(std::to_integer<uint8_t>(b[3])) << 24);
}
bool fourcc(const std::byte* b, const char* text) noexcept {
    return std::memcmp(b, text, 4) == 0;
}
std::string_view trim(std::string_view s) noexcept {
    while (!s.empty() && (s.front() == ' ' || s.front() == '\t' || s.front() == '\r'))
        s.remove_prefix(1);
    while (!s.empty() && (s.back() == ' ' || s.back() == '\t' || s.back() == '\r'))
        s.remove_suffix(1);
    return s;
}
std::string_view token(std::string_view& s) noexcept {
    s = trim(s);
    const auto end = s.find_first_of(" \t\r");
    const auto result = s.substr(0, end);
    s.remove_prefix(result.size());
    return result;
}
} // namespace
Profile::Profile() noexcept {
    for (size_t i = 0; i < parameterCount; ++i)
        values[i] = parameters[i].initial;
}
void Profile::apply(ParameterStore& store) const noexcept {
    for (size_t i = 0; i < parameterCount; ++i)
        if (present[i])
            store.set(static_cast<Param>(i), values[i]);
}
bool permitted(Kind kind, Param parameter) noexcept {
    if (kind == Kind::User)
        return parameter == Param::LowCrossover || parameter == Param::HighCrossover ||
               parameter == Param::Feedback || parameter == Param::ReverbDecay ||
               parameter == Param::NoiseColor || parameter == Param::Swing;
    if (kind != Kind::Preset)
        return false;
    return parameter != Param::Bypass && parameter != Param::WetOnly && parameter != Param::SceneOn &&
           parameter != Param::ReleaseAmount && parameter != Param::ReleaseType &&
           parameter != Param::XHold && parameter != Param::Overdub && parameter != Param::UserSettings;
}
Error decodeProfile(File& file, Kind kind, Profile& candidate) noexcept {
    if (kind != Kind::Preset && kind != Kind::User)
        return Error::Format;
    const auto bytes = file.size();
    if (!bytes || bytes > maximumProfileBytes)
        return Error::Limit;
    std::array<std::byte, maximumProfileBytes> input{};
    if (!file.seek(0) || !exact(file, std::span(input).first(bytes)))
        return Error::Read;
    std::string_view text(reinterpret_cast<const char*>(input.data()), bytes);
    if (text.find('\0') != std::string_view::npos)
        return Error::Format;
    Profile staged;
    bool header = false;
    while (!text.empty()) {
        const auto end = text.find('\n');
        auto row = trim(text.substr(0, end));
        text.remove_prefix(end == std::string_view::npos ? text.size() : end + 1);
        if (row.size() > 127)
            return Error::Limit;
        if (row.empty() || row.front() == '#')
            continue;
        if (!header) {
            if (row != (kind == Kind::User ? "RMX_USER 1" : "RMX_BOOT 1"))
                return Error::Format;
            header = true;
            continue;
        }
        if (token(row) != "param")
            return Error::Format;
        const auto id = token(row), value = token(row);
        if (id.empty() || value.empty() || value.size() > 31 || !trim(row).empty())
            return Error::Format;
        size_t index = 0;
        while (index < parameterCount && parameters[index].id != id)
            ++index;
        if (index == parameterCount || !permitted(kind, static_cast<Param>(index)) || staged.present[index])
            return Error::Value;
        if (value.find_first_not_of("+-0123456789.eE") != std::string_view::npos)
            return Error::Value;
        std::array<char, 32> numeric{};
        std::memcpy(numeric.data(), value.data(), value.size());
        char* tail{};
        errno = 0;
        const float number = std::strtof(numeric.data(), &tail);
        const auto& info = parameters[index];
        if (errno || tail != numeric.data() + value.size() || !std::isfinite(number) || number < info.min ||
            number > info.max || (info.discrete && std::round(number) != number))
            return Error::Value;
        staged.values[index] = number;
        staged.present[index] = true;
    }
    if (!header)
        return Error::Format;
    candidate = staged;
    return Error::None;
}
Error decodeWave(File& file, Sample& candidate) noexcept {
    const auto bytes = file.size();
    if (bytes < 44 || bytes > maximumWaveBytes)
        return Error::Limit;
    std::array<std::byte, 16> header{};
    if (!file.seek(0) || !exact(file, std::span(header).first(12)))
        return Error::Read;
    if (!fourcc(header.data(), "RIFF") || !fourcc(header.data() + 8, "WAVE") ||
        u32(header.data() + 4) != bytes - 8)
        return Error::Format;
    uint16_t encoding{}, channels{}, bits{}, alignment{};
    uint32_t rate{}, dataAt{}, dataBytes{};
    bool haveFormat = false, haveData = false;
    uint32_t offset = 12;
    unsigned chunks = 0;
    while (offset < bytes) {
        if (++chunks > 64 || bytes - offset < 8)
            return Error::Format;
        if (!file.seek(offset) || !exact(file, std::span(header).first(8)))
            return Error::Read;
        const uint32_t length = u32(header.data() + 4), start = offset + 8;
        if (length > bytes - start || (length & 1u) > bytes - start - length)
            return Error::Format;
        if (fourcc(header.data(), "fmt ")) {
            if (haveFormat || length < 16 || length > 64)
                return Error::Format;
            if (!exact(file, header))
                return Error::Read;
            encoding = u16(header.data());
            channels = u16(header.data() + 2);
            rate = u32(header.data() + 4);
            alignment = u16(header.data() + 12);
            bits = u16(header.data() + 14);
            if ((encoding != 1 && encoding != 3) || channels < 1 || channels > 2 || rate < 8000 ||
                rate > 96000 || (encoding == 3 && bits != 32) ||
                (encoding == 1 && bits != 16 && bits != 24 && bits != 32) ||
                alignment != channels * (bits / 8) || u32(header.data() + 8) != rate * alignment)
                return Error::Format;
            haveFormat = true;
        } else if (fourcc(header.data(), "data")) {
            if (haveData)
                return Error::Format;
            dataAt = start;
            dataBytes = length;
            haveData = true;
        }
        offset = start + length + (length & 1u);
    }
    if (!haveFormat || !haveData || !dataBytes || dataBytes % alignment)
        return Error::Format;
    const uint32_t frames = dataBytes / alignment;
    if (frames > maximumFrames || frames > rate * 2 || frames < 2)
        return Error::Limit;
    if (!file.seek(dataAt))
        return Error::Read;
    // Force even tiny optional samples through the >=4096-byte audio arena
    // path. The MCU adapter preflights its actual free blocks with audio off.
    const size_t capacity = std::max<size_t>(frames, 4096 / sizeof(Stereo));
    if (!file.canAllocate(capacity * sizeof(Stereo)))
        return Error::Memory;
    Sample staged;
    staged.rate = rate;
    staged.frames.reserve(capacity);
    staged.frames.resize(frames);
    std::array<std::byte, 4096> scratch{};
    const auto decode = [&](const std::byte* p) noexcept {
        if (encoding == 3)
            return std::bit_cast<float>(u32(p));
        if (bits == 16)
            return static_cast<int16_t>(u16(p)) / 32768.f;
        return static_cast<int32_t>(u32(p)) / 2147483648.f;
    };
    uint32_t copied = 0;
    while (copied < frames) {
        const size_t count = std::min<size_t>(frames - copied, scratch.size() / alignment);
        const size_t length = count * alignment;
        if (!exact(file, std::span(scratch).first(length)))
            return Error::Read;
        for (size_t i = 0; i < count; ++i) {
            const auto* sample = scratch.data() + i * alignment;
            // Decode 24-bit without reading a fourth byte past a mono/block end.
            auto channel = [&](const std::byte* p) {
                if (encoding == 1 && bits == 24) {
                    int32_t v = std::to_integer<uint8_t>(p[0]) | (std::to_integer<uint8_t>(p[1]) << 8) |
                                (std::to_integer<uint8_t>(p[2]) << 16);
                    if (v & 0x00800000)
                        v -= 0x01000000;
                    return v / 8388608.f;
                }
                return decode(p);
            };
            const float left = channel(sample), right = channels == 1 ? left : channel(sample + bits / 8);
            if (!std::isfinite(left) || !std::isfinite(right) || std::abs(left) > 1 || std::abs(right) > 1)
                return Error::Value;
            staged.frames[copied + i] = {left, right};
        }
        copied += static_cast<uint32_t>(count);
    }
    candidate = std::move(staged);
    return Error::None;
}
Report load(Files& files, SampleBank& bank, ParameterStore& store) noexcept {
    Report report;
    // Each cold-boot attempt begins from defaults, even if a host harness reuses a store.
    for (size_t i = 0; i < parameterCount; ++i)
        if (permitted(Kind::Preset, static_cast<Param>(i)))
            store.set(static_cast<Param>(i), parameters[i].initial);
    for (auto kind : {Kind::Preset, Kind::User}) {
        auto& result = kind == Kind::Preset ? report.preset : report.user;
        if (files.expired()) {
            result = Error::Timeout;
            report.timedOut = true;
            continue;
        }
        auto* file = files.open(kind, 0, result);
        if (!file)
            continue;
        Profile candidate;
        result = decodeProfile(*file, kind, candidate);
        if (!file->close())
            result = Error::Close;
        if (files.expired()) {
            result = Error::Timeout;
            report.timedOut = true;
        }
        if (result == Error::None)
            candidate.apply(store);
    }
    for (unsigned slot = 0; slot < 16; ++slot) {
        auto& result = report.samples[slot];
        if (files.expired()) {
            result = Error::Timeout;
            report.timedOut = true;
            continue;
        }
        auto* file = files.open(Kind::Sample, slot, result);
        if (!file)
            continue;
        Sample candidate;
        result = decodeWave(*file, candidate);
        if (!file->close())
            result = Error::Close;
        if (files.expired()) {
            result = Error::Timeout;
            report.timedOut = true;
        }
        if (result == Error::None) {
            bank.slots[slot] = std::move(candidate);
            report.loadedMask |= uint16_t(1u << slot);
        }
    }
    // Card data cannot arm processing or restore held controls.
    for (auto parameter : {Param::Bypass, Param::WetOnly, Param::SceneOn, Param::ReleaseAmount, Param::XHold,
                           Param::Overdub, Param::UserSettings})
        store.set(parameter, 0);
    return report;
}
} // namespace rmx::storage
