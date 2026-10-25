#include "../AudioMemory.h"
#include "rmx/FixedArena.h"
#include "rmx/storage/BootStorage.h"
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {
void require(bool value, const char* message) {
    if (!value)
        throw std::runtime_error(message);
}
class DefaultResource final {
  public:
    explicit DefaultResource(std::pmr::memory_resource& resource)
        : previous(std::pmr::set_default_resource(&resource)) {}
    ~DefaultResource() { std::pmr::set_default_resource(previous); }
    DefaultResource(const DefaultResource&) = delete;
    DefaultResource& operator=(const DefaultResource&) = delete;
  private:
    std::pmr::memory_resource* previous;
};
void put16(std::vector<std::byte>& bytes, uint16_t word) {
    bytes.push_back(std::byte(word));
    bytes.push_back(std::byte(word >> 8));
}
void put32(std::vector<std::byte>& bytes, uint32_t word) {
    put16(bytes, uint16_t(word));
    put16(bytes, uint16_t(word >> 16));
}
void fourcc(std::vector<std::byte>& bytes, const char* text) {
    for (unsigned i = 0; i < 4; ++i)
        bytes.push_back(std::byte(text[i]));
}
std::vector<std::byte> wave() {
    constexpr unsigned frames = 1024;
    std::vector<std::byte> bytes;
    fourcc(bytes, "RIFF"); put32(bytes, 36 + frames * 2); fourcc(bytes, "WAVE");
    fourcc(bytes, "fmt "); put32(bytes, 16); put16(bytes, 1); put16(bytes, 1);
    put32(bytes, 48000); put32(bytes, 96000); put16(bytes, 2); put16(bytes, 16);
    fourcc(bytes, "data"); put32(bytes, frames * 2);
    for (unsigned i = 0; i < frames; ++i)
        put16(bytes, i % 2 ? uint16_t(-16384) : uint16_t(16384));
    return bytes;
}
class RefusingResource final : public std::pmr::memory_resource {
  public:
    explicit RefusingResource(rmx::FixedArena& backing) : arena(backing) {}
    bool refuse{};
    size_t failures{};
  private:
    rmx::FixedArena& arena;
    void* do_allocate(size_t bytes, size_t alignment) override {
        if (refuse) {
            ++failures;
            throw std::bad_alloc();
        }
        return arena.allocate(bytes, alignment);
    }
    void do_deallocate(void* memory, size_t bytes, size_t alignment) override {
        arena.deallocate(memory, bytes, alignment);
    }
    bool do_is_equal(const std::pmr::memory_resource& other) const noexcept override {
        return this == &other;
    }
};
class WaveFile final : public rmx::storage::File {
  public:
    explicit WaveFile(std::pmr::memory_resource& target, RefusingResource* fault = nullptr)
        : resource(target), refusing(fault), bytes(wave()) {}
    uint32_t size() const noexcept override { return uint32_t(bytes.size()); }
    bool seek(uint32_t at) noexcept override {
        if (at > bytes.size()) return false;
        position = at;
        return true;
    }
    size_t read(std::span<std::byte> output) noexcept override {
        const size_t count = std::min(output.size(), bytes.size() - position);
        std::memcpy(output.data(), bytes.data() + position, count);
        position += count;
        return count;
    }
    bool close() noexcept override { return true; }
    bool canAllocate(size_t count) const noexcept override {
        ++probes;
        probedBytes = count;
        const bool result = rmx::embedded::probeAudioAllocation(&resource, count);
        probePassed = result;
        if (result && refusing)
            refusing->refuse = true;
        return result;
    }
    mutable size_t probes{}, probedBytes{};
    mutable bool probePassed{};
  private:
    std::pmr::memory_resource& resource;
    RefusingResource* refusing;
    std::vector<std::byte> bytes;
    size_t position{};
};
void baseline(rmx::Sample& sample) {
    sample.frames.push_back({.25f, -.5f});
    sample.rate = 32000;
    sample.playback = {137, true};
}
void unchanged(const rmx::Sample& sample) {
    require(sample.frames.size() == 1 && sample.frames[0].l == .25f && sample.frames[0].r == -.5f &&
                sample.rate == 32000 && sample.playback == rmx::SamplePlayback{137, true},
            "Memory error modified caller sample");
}
void fragmented() {
    alignas(std::max_align_t) std::array<std::byte, 16384> storage;
    rmx::FixedArena arena(storage.data(), storage.size());
    require(!rmx::embedded::probeAudioAllocation(nullptr, 4096), "Null resource accepted");
    require(!rmx::embedded::probeAudioAllocation(&arena, 4095), "Small allocation accepted");
    auto* first = arena.allocate(4096);
    auto* middle = arena.allocate(4096);
    auto* third = arena.allocate(4096);
    auto* tail = arena.allocate(3000);
    arena.deallocate(first, 4096);
    arena.deallocate(third, 4096);
    const auto used = arena.used();
    require(rmx::embedded::probeAudioAllocation(&arena, 4096), "Free block was not reusable");
    require(!rmx::embedded::probeAudioAllocation(&arena, 6144), "Fragmented total space accepted");
    require(arena.used() == used, "Probe leaked or retained allocation");
    {
        DefaultResource use(arena);
        rmx::Sample sample;
        baseline(sample);
        const auto before = arena.used();
        WaveFile file(arena);
        require(rmx::storage::decodeWave(file, sample) == rmx::storage::Error::Memory,
                "Fragmented actual arena did not reject sample staging");
        require(file.probes == 1 && !file.probePassed && arena.used() == before,
                "Fragmented decoder skipped the real probe or leaked storage");
        unchanged(sample);
    }
    require(arena.used() == used, "Fragmented decode retained caller storage");
    arena.deallocate(middle, 4096);
    require(rmx::embedded::probeAudioAllocation(&arena, 12288), "Coalesced block rejected");
    arena.deallocate(tail, 3000);
    require(arena.used() == 0 && rmx::embedded::probeAudioAllocation(&arena, arena.capacity()),
            "Whole arena not restored after coalescing");
}
void probeThenDecode() {
    alignas(std::max_align_t) std::array<std::byte, 32768> storage;
    rmx::FixedArena arena(storage.data(), storage.size());
    {
        DefaultResource use(arena);
        rmx::Sample sample;
        baseline(sample);
        WaveFile file(arena);
        require(rmx::storage::decodeWave(file, sample) == rmx::storage::Error::None,
                "Actual FixedArena probe-to-PMR decode failed");
        require(file.probes == 1 && file.probePassed && file.probedBytes == 1024*sizeof(rmx::Stereo),
                "Decode used a different allocation contract");
        require(sample.frames.get_allocator().resource() == &arena && sample.frames.size() == 1024 &&
                    sample.rate == 48000 && sample.frames[0].l == .5f && sample.frames[1].r == -.5f,
                "Successful decode did not publish actual arena storage/data");
    }
    require(arena.used() == 0, "Decoded sample storage leaked");
}
void failureAfterPositiveProbe() {
    alignas(std::max_align_t) std::array<std::byte, 32768> storage;
    rmx::FixedArena arena(storage.data(), storage.size());
    RefusingResource resource(arena);
    {
        DefaultResource use(resource);
        rmx::Sample sample;
        baseline(sample);
        const auto used = arena.used();
        WaveFile file(resource, &resource);
        require(rmx::storage::decodeWave(file, sample) == rmx::storage::Error::Memory,
                "Post-probe bad_alloc escaped the noexcept decoder");
        require(file.probePassed && resource.failures == 1, "Failure was not after successful real probe");
        unchanged(sample);
        require(arena.used() == used, "Failed staging leaked storage");
    }
    require(arena.used() == 0, "Failed decode retained baseline storage");
}
void mismatchedResource() {
    alignas(std::max_align_t) std::array<std::byte, 32768> storage;
    rmx::FixedArena arena(storage.data(), storage.size());
    rmx::Sample sample; // deliberately uses the resource preceding the arena
    baseline(sample);
    {
        DefaultResource use(arena);
        WaveFile file(arena);
        require(rmx::storage::decodeWave(file, sample) == rmx::storage::Error::Memory,
                "Foreign candidate allocator accepted unsafe publication");
        require(file.probes == 0 && arena.used() == 0, "Foreign allocator reached staging");
        unchanged(sample);
    }
}
} // namespace
int main() {
    try {
        fragmented();
        probeThenDecode();
        failureAfterPositiveProbe();
        mismatchedResource();
        std::cout << "Actual FixedArena fragmentation/coalescing and probe-to-PMR decode pass; post-probe bad_alloc and foreign allocators retain caller data\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
