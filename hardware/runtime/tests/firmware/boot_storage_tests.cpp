#include "TestSupport.h"
#include "hardware/firmware/AudioArena.h"
#include "rmx/Engine.h"
#include "rmx/storage/BootStorage.h"
#include <bit>
#include <cstring>
#include <memory>
#include <optional>

using namespace rmx;
using namespace rmx::storage;
namespace {
struct MemoryFile final : File {
    std::vector<std::byte> bytes;
    size_t position{}, chunk{4096}, readCalls{}, failRead{}, closeCalls{};
    uint32_t declaredSize{};
    bool seekFails{}, closeFails{}, expireOnRead{}, allocationFails{};
    bool* expiredFlag{};
    explicit MemoryFile(std::vector<std::byte> data) : bytes(std::move(data)) {}
    uint32_t size() const noexcept override {
        return declaredSize ? declaredSize : uint32_t(bytes.size());
    }
    bool seek(uint32_t offset) noexcept override {
        if (seekFails || offset > bytes.size())
            return false;
        position = offset;
        return true;
    }
    size_t read(std::span<std::byte> out) noexcept override {
        if (++readCalls == failRead)
            return 0;
        const auto count = std::min({out.size(), chunk, bytes.size() - position});
        std::memcpy(out.data(), bytes.data() + position, count);
        position += count;
        if (expireOnRead && expiredFlag)
            *expiredFlag = true;
        return count;
    }
    bool canAllocate(size_t) const noexcept override {
        return !allocationFails;
    }
    bool close() noexcept override {
        ++closeCalls;
        return !closeFails;
    }
};
struct MemoryFiles final : Files {
    std::array<std::optional<MemoryFile>, 18> entries;
    std::array<bool, 18> openFails{};
    bool timedOut{};
    size_t opens{};
    File* open(Kind kind, unsigned slot, Error& error) noexcept override {
        ++opens;
        const auto index = kind == Kind::Sample ? slot + 2 : kind == Kind::User ? 1 : 0;
        if (openFails[index]) {
            error = Error::Open;
            return nullptr;
        }
        if (!entries[index]) {
            error = Error::Missing;
            return nullptr;
        }
        auto& entry = *entries[index];
        entry.position = entry.readCalls = 0;
        entry.expiredFlag = &timedOut;
        error = Error::None;
        return &entry;
    }
    bool expired() const noexcept override {
        return timedOut;
    }
};
void put16(std::vector<std::byte>& b, uint16_t n) {
    b.push_back(std::byte(n));
    b.push_back(std::byte(n >> 8));
}
void put32(std::vector<std::byte>& b, uint32_t n) {
    put16(b, uint16_t(n));
    put16(b, uint16_t(n >> 16));
}
void word(std::vector<std::byte>& b, const char* s) {
    for (int i = 0; i < 4; ++i)
        b.push_back(std::byte(s[i]));
}
void overwrite32(std::vector<std::byte>& b, size_t at, uint32_t n) {
    for (size_t i = 0; i < 4; ++i)
        b[at + i] = std::byte(n >> (8 * i));
}
std::vector<std::byte> text(std::string_view s) {
    return {reinterpret_cast<const std::byte*>(s.data()),
            reinterpret_cast<const std::byte*>(s.data() + s.size())};
}
std::vector<std::byte> wave(uint16_t channels = 2, uint16_t bits = 16, uint16_t encoding = 1,
                            uint32_t frames = 4, bool dataFirst = false, bool oddMetadata = false) {
    std::vector<std::byte> body;
    auto format = [&] {
        word(body, "fmt ");
        put32(body, 16);
        put16(body, encoding);
        put16(body, channels);
        put32(body, 48000);
        put32(body, 48000 * channels * bits / 8);
        put16(body, channels * bits / 8);
        put16(body, bits);
    };
    auto data = [&] {
        word(body, "data");
        const auto count = frames * channels * bits / 8;
        put32(body, count);
        for (uint32_t i = 0; i < frames * channels; ++i) {
            const bool negative = i % 2;
            if (encoding == 3)
                put32(body, std::bit_cast<uint32_t>(negative ? -.5f : .5f));
            else if (bits == 16)
                put16(body, negative ? uint16_t(0xc000) : uint16_t(0x4000));
            else if (bits == 24) {
                body.push_back(std::byte{0});
                body.push_back(std::byte{0});
                body.push_back(negative ? std::byte{0xc0} : std::byte{0x40});
            } else
                put32(body, negative ? 0xc0000000 : 0x40000000);
        }
        if (count % 2)
            body.push_back(std::byte{0});
    };
    if (oddMetadata) {
        word(body, "JUNK");
        put32(body, 1);
        body.push_back(std::byte{7});
        body.push_back(std::byte{0});
    }
    if (dataFirst) {
        data();
        format();
    } else {
        format();
        data();
    }
    std::vector<std::byte> out;
    word(out, "RIFF");
    put32(out, uint32_t(body.size() + 4));
    word(out, "WAVE");
    out.insert(out.end(), body.begin(), body.end());
    return out;
}
SampleBank baseline() {
    SampleBank b;
    for (auto& s : b.slots) {
        s.rate = 48000;
        s.frames = {{.125f, .25f}, {.125f, .25f}};
    }
    return b;
}
void unchanged(const Sample& sample) {
    require(sample.frames.size() == 2 && sample.frames[0].l == .125f && sample.frames[0].r == .25f,
            "Rejected file replaced factory sample");
}
} // namespace
int main() {
    return runTests([] {
        unsigned validWaves = 0, rejectedWaves = 0, rejectedProfiles = 0, transactionFaults = 0;
        for (auto encoding : {1, 3})
            for (auto bits : {16, 24, 32})
                for (auto channels : {1, 2}) {
                    if (encoding == 3 && bits != 32)
                        continue;
                    for (bool dataFirst : {false, true})
                        for (bool odd : {false, true}) {
                            MemoryFile file(wave(channels, bits, encoding, 5, dataFirst, odd));
                            file.chunk = 3;
                            Sample candidate;
                            require(decodeWave(file, candidate) == Error::None,
                                    "Supported WAV failed partial reads/order/padding");
                            require(candidate.frames.size() == 5 && candidate.rate == 48000,
                                    "WAV rate/frame count wrong");
                            require(candidate.frames[0].l == .5f, "WAV first channel sign/scale wrong");
                            require(candidate.frames[0].r == (channels == 1 ? .5f : -.5f),
                                    "WAV channel mapping wrong");
                            ++validWaves;
                        }
                }
        MemoryFile maximumFile(wave(2, 32, 3, maximumFrames));
        Sample maximumSample;
        require(decodeWave(maximumFile, maximumSample) == Error::None &&
                    maximumSample.frames.size() == maximumFrames,
                "Maximum legal sample rejected");
        MemoryFile durationFile(wave(2, 16, 1, 20000));
        overwrite32(durationFile.bytes, 24, 8000);
        overwrite32(durationFile.bytes, 28, 32000);
        Sample durationSample;
        require(decodeWave(durationFile, durationSample) == Error::Limit,
                "Low-rate sample exceeded two-second duration cap");
        auto rejectWave = [&](std::vector<std::byte> bytes) {
            MemoryFile f(std::move(bytes));
            Sample candidate;
            candidate.frames = {{.125f, .25f}};
            require(decodeWave(f, candidate) != Error::None, "Malformed WAV accepted");
            require(candidate.frames.size() == 1 && candidate.frames[0].l == .125f,
                    "Failed decoder changed candidate");
            ++rejectedWaves;
        };
        auto b = wave();
        b.pop_back();
        rejectWave(b);
        b = wave();
        overwrite32(b, 4, 0xffffffff);
        rejectWave(b);
        b = wave();
        overwrite32(b, 40, 0xfffffff0);
        rejectWave(b);
        b = wave();
        b[32] = std::byte{7};
        rejectWave(b);
        b = wave();
        overwrite32(b, 28, 123);
        rejectWave(b);
        b = wave();
        overwrite32(b, 24, 192000);
        rejectWave(b);
        b = wave();
        b[20] = std::byte{0xfe};
        rejectWave(b);
        b = wave();
        b[22] = std::byte{3};
        rejectWave(b);
        b = wave(1, 32, 3);
        overwrite32(b, 44, 0x7fc00000);
        rejectWave(b);
        b = wave(1, 32, 3);
        overwrite32(b, 44, std::bit_cast<uint32_t>(1.5f));
        rejectWave(b);
        rejectWave(wave(2, 16, 1, maximumFrames + 1));
        rejectWave(wave(2, 16, 1, 1));
        MemoryFile oversized(wave());
        oversized.declaredSize = maximumWaveBytes + 1;
        Sample dummy;
        require(decodeWave(oversized, dummy) == Error::Limit && oversized.readCalls == 0,
                "Oversized file read/allocated");
        MemoryFile badSeek(wave());
        badSeek.seekFails = true;
        require(decodeWave(badSeek, dummy) == Error::Read, "Seek failure ignored");
        MemoryFile profile(text("# boot\nRMX_BOOT 1\r\nparam tempo 128\nparam feedback 0.4\n"));
        profile.chunk = 1;
        Profile parsed;
        require(decodeProfile(profile, Kind::Preset, parsed) == Error::None, "Valid profile failed");
        ParameterStore store;
        parsed.apply(store);
        require(store.get(Param::Tempo) == 128 && store.get(Param::Feedback) == .4f,
                "Parsed values not applied");
        for (auto input :
             {"RMX_BOOT 2\n", "RMX_BOOT 1\nparam unknown 1\n", "RMX_BOOT 1\nparam tempo nan\n",
              "RMX_BOOT 1\nparam tempo 300\n", "RMX_BOOT 1\nparam bank 1.5\n",
              "RMX_BOOT 1\nparam tempo 130\nparam tempo 131\n", "RMX_BOOT 1\nparam tempo 120 extra\n",
              "RMX_BOOT 1\nparam wet_only 1\n", "RMX_BOOT 1\nparam release_amount 1\n",
              "RMX_BOOT 1\nparam scene_on 1\n", "RMX_BOOT 1\nparam tempo 0x78\n"}) {
            MemoryFile f(text(input));
            Profile output;
            output.values[0] = 99;
            // C strtof accepts hexadecimal, so the loader must reject non-decimal input.
            const auto result = decodeProfile(f, Kind::Preset, output);
            require(result != Error::None, "Malformed/unsafe profile accepted");
            require(output.values[0] == 99, "Rejected profile modified output");
            ++rejectedProfiles;
        }
        MemoryFile badUser(text("RMX_USER 1\nparam input_gain 6\n"));
        require(decodeProfile(badUser, Kind::User, parsed) == Error::Value,
                "User profile overrode physical gain");
        MemoryFiles missing;
        auto bank = baseline();
        store.set(Param::Tempo, 200);
        store.set(Param::WetOnly, 1);
        auto report = load(missing, bank, store);
        require(report.loadedMask == 0 && report.preset == Error::Missing && store.get(Param::Tempo) == 120 &&
                    store.get(Param::WetOnly) == 0,
                "Missing card reused stale parameters");
        unchanged(bank.slots[0]);
        MemoryFiles success;
        success.entries[0].emplace(text("RMX_BOOT 1\nparam tempo 130\nparam feedback 0.4\n"));
        success.entries[1].emplace(text("RMX_USER 1\nparam feedback 0.7\n"));
        success.entries[2].emplace(wave());
        report = load(success, bank, store);
        require(report.loadedMask == 1 && store.get(Param::Tempo) == 130 && store.get(Param::Feedback) == .7f,
                "Asset load/user override failed");
        require(success.entries[0]->closeCalls == 1 && success.entries[1]->closeCalls == 1 &&
                    success.entries[2]->closeCalls == 1,
                "Asset handles leaked");
        for (size_t call = 1; call <= 6; ++call) {
            MemoryFiles failed;
            failed.entries[2].emplace(wave());
            failed.entries[2]->failRead = call;
            failed.entries[2]->chunk = 7;
            auto factory = baseline();
            auto result = load(failed, factory, store);
            require(result.loadedMask == 0 && result.samples[0] == Error::Read,
                    "Injected read failure committed");
            unchanged(factory.slots[0]);
            ++transactionFaults;
        }
        for (bool profileFile : {false, true}) {
            MemoryFiles failed;
            const size_t index = profileFile ? 0 : 2;
            failed.entries[index].emplace(profileFile ? text("RMX_BOOT 1\nparam tempo 140\n") : wave());
            failed.entries[index]->closeFails = true;
            auto factory = baseline();
            auto result = load(failed, factory, store);
            require(result.loadedMask == 0 && store.get(Param::Tempo) == 120,
                    "Close failure committed staged asset");
            unchanged(factory.slots[0]);
            ++transactionFaults;
        }
        MemoryFiles timeout;
        timeout.entries[2].emplace(wave());
        timeout.entries[2]->expireOnRead = true;
        auto factory = baseline();
        report = load(timeout, factory, store);
        require(report.timedOut && report.loadedMask == 0 && timeout.opens == 3,
                "Expired budget opened more assets or committed data");
        unchanged(factory.slots[0]);
        MemoryFiles memoryError;
        memoryError.entries[2].emplace(wave());
        memoryError.entries[2]->allocationFails = true;
        auto memoryFactory = baseline();
        auto memoryReport = load(memoryError, memoryFactory, store);
        require(memoryReport.samples[0] == Error::Memory && memoryReport.loadedMask == 0,
                "Arena refusal did not preserve factory sample");
        unchanged(memoryFactory.slots[0]);
        alignas(16) std::array<std::byte, 12288> arenaMemory;
        rmx::embedded::AudioArena arena;
        require(arena.initialize(arenaMemory.data(), arenaMemory.size()), "Test arena initialization failed");
        auto* first = arena.allocate(4096);
        auto* middle = arena.allocate(4096);
        auto* last = arena.allocate(4096);
        require(first && middle && last && !arena.canAllocate(1), "Full arena preflight accepted allocation");
        require(arena.release(first) && arena.release(last), "Test arena release failed");
        require(arena.canAllocate(4096) && !arena.canAllocate(6144),
                "Fragmented arena preflight used total free bytes instead of contiguous space");
        require(arena.release(middle) && arena.canAllocate(12288),
                "Coalesced arena preflight rejected full span");
        MemoryFiles openError;
        openError.openFails[2] = true;
        report = load(openError, factory, store);
        require(report.samples[0] == Error::Open && report.loadedMask == 0, "Open error ignored");
        std::cout << "Boot storage: " << validWaves << " valid WAV combinations; " << rejectedWaves
                  << " malformed WAVs; " << rejectedProfiles << " rejected profiles; " << transactionFaults
                  << " staged transaction faults; missing/open/timeout/arena-exhaustion and "
                     "fragmented-free-block fallback passed\n";
    });
}
