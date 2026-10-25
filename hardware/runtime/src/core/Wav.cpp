#include "rmx/Wav.h"
#include <bit>
#include <cstring>
#include <fstream>
#include <limits>
#include <stdexcept>

namespace rmx {
namespace {
uint16_t u16(const unsigned char* p) {
    return static_cast<uint16_t>(p[0] | (p[1] << 8));
}
uint32_t u32(const unsigned char* p) {
    return uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}
void put16(std::ostream& o, uint16_t n) {
    char b[2]{static_cast<char>(n), static_cast<char>(n >> 8)};
    o.write(b, 2);
}
void put32(std::ostream& o, uint32_t n) {
    char b[4]{static_cast<char>(n), static_cast<char>(n >> 8), static_cast<char>(n >> 16),
              static_cast<char>(n >> 24)};
    o.write(b, 4);
}
} // namespace
Sample readWav(const std::filesystem::path& path, double maxSeconds) {
    std::ifstream in(path, std::ios::binary);
    if (!in)
        throw std::runtime_error("Cannot open WAV: " + path.string());
    unsigned char header[12]{};
    in.read(reinterpret_cast<char*>(header), 12);
    if (!in || std::memcmp(header, "RIFF", 4) || std::memcmp(header + 8, "WAVE", 4))
        throw std::runtime_error("Expected RIFF/WAVE file");
    uint16_t format = 0, channels = 0, bits = 0, align = 0;
    uint32_t rate = 0;
    std::streampos dataPos{};
    uint32_t dataSize = 0;
    while (in) {
        unsigned char h[8];
        in.read(reinterpret_cast<char*>(h), 8);
        if (!in)
            break;
        const auto size = u32(h + 4);
        const auto start = in.tellg();
        if (!std::memcmp(h, "fmt ", 4)) {
            if (size < 16 || size > 65536)
                throw std::runtime_error("Invalid WAV format chunk");
            std::vector<unsigned char> f(size);
            in.read(reinterpret_cast<char*>(f.data()), size);
            if (!in)
                throw std::runtime_error("Truncated WAV format");
            format = u16(f.data());
            channels = u16(f.data() + 2);
            rate = u32(f.data() + 4);
            align = u16(f.data() + 12);
            bits = u16(f.data() + 14);
            if (format == 0xfffe && size >= 40)
                format = u16(f.data() + 24);
        } else if (!std::memcmp(h, "data", 4)) {
            dataPos = start;
            dataSize = size;
        }
        in.seekg(start + static_cast<std::streamoff>(size + (size & 1)));
        if (format && dataSize)
            break;
    }
    if ((format != 1 && format != 3) || channels < 1 || channels > 2 || rate < 8000 || rate > 192000 ||
        !align || !dataSize)
        throw std::runtime_error("Unsupported WAV: use mono/stereo PCM or float, 8–192 kHz");
    if ((format == 3 && bits != 32) || (format == 1 && bits != 16 && bits != 24 && bits != 32) ||
        align != channels * (bits / 8) || dataSize % align)
        throw std::runtime_error("Unsupported WAV sample encoding");
    const size_t frames = dataSize / align;
    if (frames > static_cast<size_t>(maxSeconds * rate))
        throw std::runtime_error("WAV exceeds maximum duration");
    std::vector<unsigned char> bytes(dataSize);
    in.clear();
    in.seekg(dataPos);
    in.read(reinterpret_cast<char*>(bytes.data()), dataSize);
    if (!in)
        throw std::runtime_error("Truncated WAV audio data");
    Sample sample;
    sample.rate = rate;
    sample.frames.resize(frames);
    auto decode = [&](const unsigned char* p) {
        float v = 0;
        if (format == 3)
            v = std::bit_cast<float>(u32(p));
        else if (bits == 16)
            v = static_cast<int16_t>(u16(p)) / 32768.f;
        else if (bits == 24) {
            int32_t n = int32_t(p[0]) | (int32_t(p[1]) << 8) | (int32_t(p[2]) << 16);
            if (n & 0x800000)
                n |= static_cast<int32_t>(0xff000000);
            v = n / 8388608.f;
        } else
            v = static_cast<int32_t>(u32(p)) / 2147483648.f;
        return std::isfinite(v) ? std::clamp(v, -8.f, 8.f) : 0.f;
    };
    for (size_t i = 0; i < frames; ++i) {
        const auto* p = bytes.data() + i * align;
        float l = decode(p), r = channels == 2 ? decode(p + bits / 8) : l;
        sample.frames[i] = {l, r};
    }
    return sample;
}
void writeWav(const std::filesystem::path& path, const Sample& sample) {
    if (sample.frames.size() > (std::numeric_limits<uint32_t>::max() - 36) / 8)
        throw std::runtime_error("WAV too large");
    std::ofstream out(path, std::ios::binary);
    if (!out)
        throw std::runtime_error("Cannot create WAV");
    const auto bytes = static_cast<uint32_t>(sample.frames.size() * 8);
    out.write("RIFF", 4);
    put32(out, 36 + bytes);
    out.write("WAVEfmt ", 8);
    put32(out, 16);
    put16(out, 3);
    put16(out, 2);
    put32(out, static_cast<uint32_t>(sample.rate));
    put32(out, static_cast<uint32_t>(sample.rate) * 8);
    put16(out, 8);
    put16(out, 32);
    out.write("data", 4);
    put32(out, bytes);
    for (auto frame : sample.frames) {
        put32(out, std::bit_cast<uint32_t>(frame.l));
        put32(out, std::bit_cast<uint32_t>(frame.r));
    }
    if (!out)
        throw std::runtime_error("WAV write failed");
}
} // namespace rmx
