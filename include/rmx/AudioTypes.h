#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace rmx {
struct Stereo {
    float l{}, r{};
};
inline Stereo operator+(Stereo a, Stereo b) {
    return {a.l + b.l, a.r + b.r};
}
inline Stereo operator-(Stereo a, Stereo b) {
    return {a.l - b.l, a.r - b.r};
}
inline Stereo operator*(Stereo a, float s) {
    return {a.l * s, a.r * s};
}
inline Stereo mix(Stereo a, Stereo b, float t) {
    return a * (1 - t) + b * t;
}
struct Sample {
    std::vector<Stereo> frames;
    double rate{48000};
};
struct SampleBank {
    std::array<Sample, 16> slots;
};
// Non-owning bank for adapters that share immutable sample payloads. Every
// referenced sample must outlive the process() call that uses this view.
struct SampleBankView {
    std::array<const Sample*, 16> slots{};
    SampleBankView() = default;
    explicit SampleBankView(const SampleBank* bank) noexcept {
        if (bank)
            for (size_t i = 0; i < slots.size(); ++i)
                slots[i] = &bank->slots[i];
    }
};
SampleBank makeFactoryBank(double rate = 48000);

enum class EventType : uint8_t { Trigger, RollStart, RollStop, Tap, ClearSequence, Panic };
struct Event {
    EventType type{};
    uint8_t pad{};
    float velocity{1};
    uint32_t offset{};
};
struct Transport {
    double bpm{120};
    double beat{};
    bool synced{}, playing{true};
};
} // namespace rmx
