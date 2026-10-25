#pragma once
#include "WireFormat.h"
#include "daisy.h"
#include <cstring>

namespace rmx::embedded {
class Calibration {
  public:
    struct Record {
        uint32_t magic{0x524d5843};
        uint16_t version{1}, home{};
        uint32_t sequence{};
        int16_t travel{};
        uint16_t reserved{};
        uint32_t crc{};
    };
    static_assert(sizeof(Record) == 20);
    explicit Calibration(daisy::QSPIHandle& q) : qspi(q) {}
    bool load() {
        const auto a = read(0), b = read(1);
        const bool av = valid(a), bv = valid(b);
        if (!av && !bv) {
            calibrated = false;
            return false;
        }
        slot = bv && (!av || static_cast<int32_t>(b.sequence - a.sequence) > 0) ? 1 : 0;
        current = slot ? b : a;
        calibrated = true;
        return true;
    }
    // Only call with relay disabled, dry bypass selected and audio stopped.
    bool save(uint16_t home, uint16_t end) {
        Record next;
        next.home = home;
        next.travel = angleDifference(end, home);
        next.sequence = current.sequence + 1;
        next.crc = checksum(next);
        if (!valid(next))
            return false;
        const uint32_t target = slot ^ 1, offset = address(target);
        if (qspi.Erase(offset, offset + 4096) != daisy::QSPIHandle::Result::OK)
            return false;
        if (qspi.Write(offset, sizeof(next), reinterpret_cast<uint8_t*>(&next)) !=
            daisy::QSPIHandle::Result::OK)
            return false;
        const auto written = read(target);
        if (!valid(written) || written.sequence != next.sequence)
            return false;
        current = written;
        slot = target;
        calibrated = true;
        return true;
    }
    bool ready() const {
        return calibrated;
    }
    float position(uint16_t raw) const {
        return calibrated ? leverPosition(raw, current.home, current.travel) : 0;
    }
    bool plausible(uint16_t raw) const {
        if (!calibrated)
            return false;
        const float fraction = static_cast<float>(angleDifference(raw, current.home)) / current.travel;
        return fraction >= -.1f && fraction <= 1.1f;
    }

  private:
    daisy::QSPIHandle& qspi;
    Record current{};
    uint32_t slot{};
    bool calibrated{};
    static uint32_t address(uint32_t index) {
        return 0x007f0000 + 4096 * index;
    }
    static uint32_t checksum(const Record& r) {
        const auto* data = reinterpret_cast<const uint8_t*>(&r);
        uint32_t crc = 0xffffffff;
        for (size_t i = 0; i < 16; ++i) {
            crc ^= data[i];
            for (int bit = 0; bit < 8; ++bit)
                crc = (crc >> 1) ^ (0xedb88320u & uint32_t(-int32_t(crc & 1)));
        }
        return ~crc;
    }
    static bool valid(const Record& r) {
        return r.magic == 0x524d5843 && r.version == 1 && r.home < 4096 && std::abs(int(r.travel)) >= 200 &&
               std::abs(int(r.travel)) <= 700 && r.crc == checksum(r);
    }
    Record read(uint32_t index) {
        Record r;
        auto* data = static_cast<uint8_t*>(qspi.GetData(address(index)));
        dsy_dma_invalidate_cache_for_buffer(data, 32);
        std::memcpy(&r, data, sizeof(r));
        return r;
    }
};
} // namespace rmx::embedded
