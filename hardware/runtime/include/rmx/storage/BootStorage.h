#pragma once
#include "rmx/AudioTypes.h"
#include "rmx/Parameters.h"
#include <span>

namespace rmx::storage {
inline constexpr uint32_t maximumFrames = 96000;
inline constexpr uint32_t maximumWaveBytes = 1024 * 1024;
inline constexpr uint32_t maximumProfileBytes = 4096;
inline constexpr size_t maximumBankPayload = 16 * maximumFrames * sizeof(Stereo);
enum class Error : uint8_t { None, Missing, Open, Read, Close, Format, Limit, Value, Timeout, Memory };
enum class Kind : uint8_t { Preset, User, Sample };
class File {
  public:
    virtual ~File() = default;
    virtual uint32_t size() const noexcept = 0;
    virtual bool seek(uint32_t offset) noexcept = 0;
    virtual size_t read(std::span<std::byte> bytes) noexcept = 0;
    virtual bool close() noexcept = 0;
    // Cold-boot adapter may reject staging before vector allocation. No other
    // arena allocations may interleave the check and the following reserve.
    virtual bool canAllocate(size_t) const noexcept {
        return true;
    }
};
class Files {
  public:
    virtual ~Files() = default;
    virtual File* open(Kind kind, unsigned slot, Error& error) noexcept = 0;
    virtual bool expired() const noexcept = 0;
};
struct Profile {
    std::array<float, parameterCount> values{};
    std::array<bool, parameterCount> present{};
    Profile() noexcept;
    void apply(ParameterStore& parameters) const noexcept;
};
struct Report {
    Error preset{Error::Missing}, user{Error::Missing};
    std::array<Error, 16> samples{};
    uint16_t loadedMask{};
    bool timedOut{};
    Report() noexcept {
        samples.fill(Error::Missing);
    }
};
// Decode into a private candidate. Callers commit only after successful close.
Error decodeWave(File& file, Sample& candidate) noexcept;
Error decodeProfile(File& file, Kind kind, Profile& candidate) noexcept;
// Cold boot only: factory bank supplied by caller, no audio callback running.
// Each asset is independent and transactional; rejected samples retain factory data.
Report load(Files& files, SampleBank& bank, ParameterStore& parameters) noexcept;
bool permitted(Kind kind, Param parameter) noexcept;
} // namespace rmx::storage
