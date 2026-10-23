#include "TestSupport.h"
#include "src/plugin/RMXProcessor.h"
#include <atomic>
#include <cstddef>
#include <cstdlib>
#include <limits>
#include <thread>

namespace {
struct alignas(__STDCPP_DEFAULT_NEW_ALIGNMENT__) Allocation {
    size_t bytes;
};
std::atomic<size_t> liveBytes{};
std::atomic<bool> callbackAllocated{}, callbackDeleted{};
thread_local bool inCallback{};
} // namespace
void* operator new(size_t bytes) {
    if (bytes > std::numeric_limits<size_t>::max() - sizeof(Allocation))
        throw std::bad_alloc();
    auto* allocation = static_cast<Allocation*>(std::malloc(sizeof(Allocation) + (bytes ? bytes : 1)));
    if (!allocation)
        throw std::bad_alloc();
    allocation->bytes = bytes;
    liveBytes.fetch_add(bytes, std::memory_order_relaxed);
    if (inCallback)
        callbackAllocated.store(true);
    return allocation + 1;
}
void operator delete(void* pointer) noexcept {
    if (!pointer)
        return;
    auto* allocation = static_cast<Allocation*>(pointer) - 1;
    liveBytes.fetch_sub(allocation->bytes, std::memory_order_relaxed);
    if (inCallback)
        callbackDeleted.store(true);
    std::free(allocation);
}
void* operator new[](size_t bytes) {
    return ::operator new(bytes);
}
void operator delete[](void* pointer) noexcept {
    ::operator delete(pointer);
}
void operator delete(void* pointer, size_t) noexcept {
    ::operator delete(pointer);
}
void operator delete[](void* pointer, size_t) noexcept {
    ::operator delete(pointer);
}

int main() {
    juce::ScopedJuceInitialiser_GUI juce;
    return runTests([] {
        const auto path =
            std::filesystem::temp_directory_path() /
            ("rmx-assets-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()) +
             ".wav");
        struct Cleanup {
            std::filesystem::path path;
            ~Cleanup() {
                std::filesystem::remove(path);
            }
        } cleanup{path};
        {
            rmx::Sample sample;
            sample.frames.resize(48000, {-.2f, -.2f});
            rmx::writeWav(path, sample);
        }
        RMXProcessor processor;
        processor.setRateAndBufferSizeDetails(48000, 128);
        processor.prepareToPlay(48000, 128);
        const juce::File file(path.string());
        const auto before = liveBytes.load();
        for (unsigned i = 0; i < 16; ++i)
            processor.importSample(0, file);
        require(liveBytes.load() < before + 2 * 48000 * sizeof(rmx::Stereo) + 1024 * 1024,
                "Stopped plugin retained superseded sample banks");

        juce::AudioBuffer<float> buffer(2, 128);
        juce::MidiBuffer midi;
        processor.engine.params.set(rmx::Param::Quantize, 0);
        processor.engine.enqueue({rmx::EventType::Trigger, 0});
        auto process = [&] {
            buffer.clear();
            inCallback = true;
            processor.processBlock(buffer, midi);
            inCallback = false;
        };
        process();
        require(std::abs(buffer.getSample(0, 64) + .15f) < 1.e-6f,
                "Audio callback did not adopt the latest imported sample");
        std::atomic<bool> finished{};
        std::thread reader([&] {
            while (!finished.load(std::memory_order_acquire))
                process();
        });
        for (unsigned i = 0; i < 64; ++i)
            processor.importSample(0, file);
        finished.store(true, std::memory_order_release);
        reader.join();
        require(!callbackAllocated.load() && !callbackDeleted.load(),
                "Plugin callback allocated or reclaimed assets during concurrent imports");
    });
}
