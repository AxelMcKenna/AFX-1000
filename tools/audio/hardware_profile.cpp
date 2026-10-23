#include "rmx/Engine.h"
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <new>

// Single-threaded profiling executable. Header storage is outside counted payload.
namespace {
struct alignas(std::max_align_t) Header {
    size_t bytes;
    bool counted;
};
size_t liveBytes{}, peakBytes{}, allocations{};
bool measuring{};
} // namespace
void* operator new(size_t bytes) {
    auto* h = static_cast<Header*>(std::malloc(sizeof(Header) + (bytes ? bytes : 1)));
    if (!h)
        throw std::bad_alloc();
    h->bytes = bytes;
    h->counted = measuring;
    if (measuring) {
        liveBytes += bytes;
        peakBytes = std::max(peakBytes, liveBytes);
        ++allocations;
    }
    return h + 1;
}
void operator delete(void* p) noexcept {
    if (!p)
        return;
    auto* h = static_cast<Header*>(p) - 1;
    if (h->counted)
        liveBytes -= h->bytes;
    std::free(h);
}
void* operator new[](size_t bytes) {
    return ::operator new(bytes);
}
void operator delete[](void* p) noexcept {
    ::operator delete(p);
}
void operator delete(void* p, size_t) noexcept {
    ::operator delete(p);
}
void operator delete[](void* p, size_t) noexcept {
    ::operator delete(p);
}

int main(int argc, char** argv) {
    const double rate = argc > 1 ? std::strtod(argv[1], nullptr) : 48000;
    if (rate != 44100 && rate != 48000 && rate != 96000) {
        std::fprintf(stderr, "Usage: rmx_hardware_profile [44100|48000|96000]\n");
        return 1;
    }
    measuring = true;
    auto bank = rmx::makeFactoryBank(rate);
    const size_t bankBytes = liveBytes;
    rmx::Engine engine;
    engine.setBank(&bank);
    engine.prepare(rate, 128);
    const size_t prepared = liveBytes;
    const size_t preparePeak = peakBytes;
    const size_t beforeProcessing = allocations;
    std::array<float, 128> left{}, right{}, outL{}, outR{};
    engine.params.set(rmx::Param::Quantize, 0);
    engine.params.set(rmx::Param::IsolateMode, 2);
    engine.params.set(rmx::Param::Low, 1);
    engine.params.set(rmx::Param::Mid, 1);
    engine.params.set(rmx::Param::High, 1);
    engine.params.set(rmx::Param::SceneOn, 1);
    engine.params.set(rmx::Param::SceneDepth, 1);
    for (int block = 0; block < 2000; ++block) {
        engine.params.set(rmx::Param::SceneType, static_cast<float>((block / 100) % 10));
        if (block % 100 == 0)
            for (int pad = 0; pad < 4; ++pad)
                engine.enqueue({rmx::EventType::Trigger, static_cast<uint8_t>(pad)});
        engine.process(left.data(), right.data(), outL.data(), outR.data(), 128);
    }
    const size_t processingAllocations = allocations - beforeProcessing;
    measuring = false;
    const size_t buffers = prepared - bankBytes;
    const size_t maxBank = static_cast<size_t>(rate * 32) * sizeof(rmx::Stereo);
    const size_t targetHeap = 48 * 1024 * 1024;
    std::printf("{\n  \"sample_rate\": %.0f,\n  \"engine_object_bytes\": %zu,\n"
                "  \"factory_sample_payload_bytes\": %zu,\n  \"engine_heap_payload_bytes\": %zu,\n"
                "  \"prepared_heap_payload_bytes\": %zu,\n  \"prepare_peak_heap_payload_bytes\": %zu,\n"
                "  \"audio_processing_allocations\": %zu,\n  \"sample_bank_limit_seconds\": 32,\n"
                "  \"maximum_bank_payload_bytes\": %zu,\n  \"heap_budget_bytes\": %zu,\n"
                "  \"maximum_bank_plus_engine_bytes\": %zu,\n  \"within_heap_payload_budget\": %s\n}\n",
                rate, sizeof(engine), bankBytes, buffers, prepared, preparePeak, processingAllocations,
                maxBank, targetHeap, maxBank + buffers, maxBank + buffers <= targetHeap ? "true" : "false");
    return processingAllocations == 0 && maxBank + buffers <= targetHeap ? 0 : 2;
}
