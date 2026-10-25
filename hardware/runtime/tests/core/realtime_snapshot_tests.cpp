#include "TestSupport.h"
#include "rmx/realtime/RealtimeSnapshot.h"
#include <atomic>
#include <thread>

namespace {
thread_local bool audioThread{};
std::atomic<unsigned> live{}, peak{};
std::atomic<bool> destroyedOnAudio{};
struct Payload {
    unsigned sequence;
    std::array<unsigned, 256> data;
    explicit Payload(unsigned sequence) : sequence(sequence) {
        data.fill(sequence);
        const auto count = live.fetch_add(1) + 1;
        auto previous = peak.load();
        while (previous < count && !peak.compare_exchange_weak(previous, count)) {
        }
    }
    ~Payload() {
        if (audioThread)
            destroyedOnAudio.store(true);
        live.fetch_sub(1);
    }
};
struct Snapshot {
    std::shared_ptr<const Payload> payload;
    explicit Snapshot(unsigned sequence) : payload(std::make_shared<const Payload>(sequence)) {}
};
} // namespace

int main() {
    return runTests([] {
        {
            rmx::RealtimeSnapshot<Snapshot> snapshot(Snapshot{0});
            // An indefinitely stopped reader must not retain every publication.
            for (unsigned i = 1; i <= 1000; ++i) {
                snapshot.publish(Snapshot{i});
                require(live.load() <= 2, "Stopped reader retained superseded assets");
            }
            require(snapshot.read().payload->sequence == 1000, "Reader missed latest stopped publication");
            constexpr unsigned last = 100000;
            std::atomic<bool> consistent{true};
            std::thread reader([&] {
                audioThread = true;
                unsigned previous = 1000;
                for (;;) {
                    const auto& payload = *snapshot.read().payload;
                    if (payload.sequence < previous)
                        consistent.store(false);
                    previous = payload.sequence;
                    for (auto value : payload.data)
                        if (value != payload.sequence)
                            consistent.store(false);
                    if (previous == last)
                        break;
                }
                audioThread = false;
            });
            for (unsigned i = 1001; i <= last; ++i)
                snapshot.publish(Snapshot{i});
            reader.join();
            require(consistent.load(), "Concurrent reader observed torn or obsolete assets");
            require(peak.load() <= 3, "Snapshot ownership exceeded three slots");
            require(!destroyedOnAudio.load(), "Asset destruction occurred on the audio thread");
        }
        require(live.load() == 0, "Snapshot destruction leaked assets");
    });
}
