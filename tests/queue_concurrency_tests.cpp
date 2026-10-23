#include "TestSupport.h"
#include "rmx/SpscQueue.h"
#include <atomic>
#include <thread>

int main() {
    return runTests([] {
        rmx::SpscQueue<uint32_t, 8> queue;
        constexpr uint32_t count = 500000;
        std::atomic<bool> ordered{true};
        std::thread producer([&] {
            for (uint32_t i = 0; i < count; ++i)
                while (!queue.push(i))
                    std::this_thread::yield();
        });
        std::thread consumer([&] {
            for (uint32_t expected = 0; expected < count; ++expected) {
                uint32_t actual{};
                while (!queue.pop(actual))
                    std::this_thread::yield();
                if (actual != expected)
                    ordered.store(false);
            }
        });
        producer.join();
        consumer.join();
        require(ordered.load(), "Concurrent queue lost or reordered data across wraparound");
        uint32_t extra{};
        require(!queue.pop(extra), "Concurrent queue retained phantom data");
    });
}
