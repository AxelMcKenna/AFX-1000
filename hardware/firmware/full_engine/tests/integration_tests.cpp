#include "../ControlReset.h"
#include "rmx/controls/HardwareControls.h"
#include "rmx/storage/BootStorage.h"
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
void require(bool value, const char* text) {
    if (!value)
        throw std::runtime_error(text);
}
struct TextFile final : rmx::storage::File {
    std::string text;
    size_t position{};
    explicit TextFile(std::string value) : text(std::move(value)) {}
    uint32_t size() const noexcept override {
        return static_cast<uint32_t>(text.size());
    }
    bool seek(uint32_t at) noexcept override {
        if (at > text.size())
            return false;
        position = at;
        return true;
    }
    size_t read(std::span<std::byte> bytes) noexcept override {
        const auto n = std::min({bytes.size(), text.size() - position, size_t(17)});
        std::memcpy(bytes.data(), text.data() + position, n);
        position += n;
        return n;
    }
    bool close() noexcept override {
        return true;
    }
};
} // namespace
void priorityResetIntegration() {
    using rmx::Param;
    using K = rmx::hardware::Knob;
    rmx::Engine engine;
    auto bank = rmx::makeFactoryBank(48000, false);
    engine.setBank(&bank);
    engine.prepare(48000, 128);
    engine.params.set(Param::Quantize, 0);
    engine.params.set(Param::SampleSource, 0);
    engine.params.set(Param::SceneOn, 1);
    engine.params.set(Param::XHold, 1);
    engine.params.set(Param::Overdub, 1);
    engine.params.set(Param::Low, .7f);
    size_t queued = 0;
    while (queued < 300 && engine.enqueue({rmx::EventType::Trigger, 0}))
        ++queued;
    require(queued > 0 && queued < 300, "Event queue did not saturate");
    require(!engine.enqueue({rmx::EventType::Panic}), "Queue-full regression did not reject ordinary Panic");
    rmx::embedded::PriorityControlReset reset;
    reset.request();
    const auto ticket = reset.begin(true);
    require(ticket.reset && reset.pending(), "Priority reset disappeared before callback processing");
    std::array<float, 128> left{}, right{};
    const rmx::Event panic{rmx::EventType::Panic};
    auto process = [&](rmx::embedded::PriorityControlReset::Ticket current) {
        engine.process(nullptr, nullptr, left.data(), right.data(), 128, {},
                       current.reset ? std::span<const rmx::Event>(&panic, 1)
                                     : std::span<const rmx::Event>{});
        reset.complete(current);
    };
    process(ticket);
    require(!reset.pending(), "Completed reset was not acknowledged");
    for (size_t i = 0; i < left.size(); ++i)
        require(left[i] == 0 && right[i] == 0, "Queued pad action ran after direct offset-zero Panic");
    require(engine.params.get(Param::SceneOn) == 0 && engine.params.get(Param::XHold) == 0 &&
                engine.params.get(Param::Overdub) == 0 && engine.params.get(Param::Low) == 0,
            "Saturated-queue priority Panic did not clear gesture state");
    // Physical bands must be restored after acknowledgement, with fresh knob
    // seen/history state, otherwise a delayed Panic erases their first readings.
    rmx::hardware::Controls restored(engine);
    restored.initializeButtons(0);
    restored.knob(K::Low, .75f);
    restored.knob(K::Mid, .25f);
    restored.knob(K::High, .6f);
    restored.knob(K::SceneDepth, .8f);
    const auto next = reset.begin(true);
    require(!next.reset && engine.params.get(Param::SceneOn) == 0, "Re-prime depth sample engaged Scene FX");
    process(next);
    require(engine.params.get(Param::Low) == .5f && engine.params.get(Param::Mid) == -.5f &&
                std::abs(engine.params.get(Param::High) - .2f) < 1e-6f,
            "Acknowledged reset later erased restored physical band positions");
    reset.request();
    const auto first = reset.begin(true);
    reset.request(); // Simulate a new foreground fault while this ticket is in flight.
    process(first);
    require(reset.pending(), "In-flight reset incorrectly acknowledged a newer request");
    const auto later = reset.begin(true);
    require(later.reset, "Late fault did not receive its own reset");
    process(later);
    require(!reset.pending(), "Late reset did not complete");
    const auto stale = reset.begin(false);
    require(stale.reset && reset.takeStaleObservation(), "Callback staleness did not notify foreground");
    process(stale);
    require(!reset.takeStaleObservation() && !reset.begin(false).reset,
            "Unchanged stale episode repeated Panic after its acknowledgement");
    std::cout << "F06 callback recovery: " << queued
              << " queued pad actions, rejected ordinary Panic, direct priority reset, late-ticket "
                 "acknowledgement and post-ack physical-band restoration pass\n";
}
int main() {
    try {
        priorityResetIntegration();
        using rmx::Param;
        using B = rmx::hardware::Button;
        using K = rmx::hardware::Knob;
        require(rmx::parameterCount > 100, "Wrong legacy DSP selected");
        rmx::Engine engine;
        auto bank = rmx::makeFactoryBank(48000, false);
        engine.setBank(&bank);
        engine.prepare(48000, 128);
        engine.params.set(Param::Quantize, 0);
        rmx::hardware::Controls controls(engine);
        auto click = [&](B b, uint32_t now) {
            controls.button(b, true, now);
            controls.button(b, false, now + 20);
        };
        controls.initializeButtons(uint32_t{1} << static_cast<unsigned>(B::Quantize));
        controls.button(B::Quantize, false, 100);
        require(engine.params.get(Param::Quantize) == 0, "Boot-held button fired on release");
        click(B::Quantize, 150);
        require(engine.params.get(Param::Quantize) == 1, "Released button did not rearm");
        engine.params.set(Param::Quantize, 0);
        controls.knob(K::SceneDepth, .6f);
        require(engine.params.get(Param::SceneOn) == 0, "Boot knob armed effect");
        controls.knob(K::SceneDepth, .61f);
        require(engine.params.get(Param::SceneOn) == 1, "Depth movement lost");
        engine.params.set(Param::SceneOn, 0);
        controls.button(B::Bank, true, 200);
        click(B::Pad2, 220);
        controls.button(B::Bank, false, 260);
        require(engine.params.get(Param::Bank) == 2 && engine.params.get(Param::SampleSource) == 1,
                "Shared bank/pad chord lost");
        controls.button(B::Bank, true, 300);
        click(B::Pad2, 320);
        controls.button(B::Bank, false, 360);
        require(engine.params.get(Param::SampleSource) == 0, "Internal factory selection lost");
        click(B::Pad0, 400);
        std::array<float, 128> left{}, right{};
        double energy = 0;
        for (int block = 0; block < 32; ++block) {
            engine.process(nullptr, nullptr, left.data(), right.data(), 128);
            for (float v : left) {
                require(std::isfinite(v), "Nonfinite audio");
                energy += v * v;
            }
        }
        require(energy > .01, "Full engine factory path is silent");
        click(B::Overdub, 500);
        require(engine.params.get(Param::Overdub) == 1, "Short Overdub lost");
        controls.button(B::Overdub, true, 600);
        controls.tick(1300);
        controls.button(B::Overdub, false, 1310);
        require(engine.params.get(Param::Overdub) == 0, "Long release accidentally restarted recording");
        click(B::Overdub, 1400);
        require(engine.params.get(Param::Overdub) == 1, "Long action left modifier latched");
        controls.button(B::Overdub, true, 1500);
        click(B::Pad1, 1600);
        controls.tick(2300);
        controls.button(B::Overdub, false, 2310);
        require(engine.params.get(Param::Overdub) == 1, "Pad modifier became a long global clear");
        controls.button(B::Hold, true, 2400);
        controls.tick(3100);
        controls.button(B::Hold, false, 3110);
        require(engine.params.get(Param::SamplerMute) == 1 && engine.params.get(Param::XHold) == 0,
                "Long Hold release changed hold state");
        require(!controls.releaseSelection(true, true), "Invalid release endpoints accepted");
        controls.release(1);
        controls.release(.5f, false);
        require(engine.params.get(Param::ReleaseAmount) == 0, "Invalid lever did not fail closed");
        std::string profile = "RMX_USER 1\n";
        size_t advanced = 0;
        for (size_t i = 0; i < rmx::parameterCount; ++i) {
            const auto p = static_cast<Param>(i);
            require(rmx::storage::permitted(rmx::storage::Kind::User, p) == rmx::parameters[i].advanced,
                    "User setting parity differs");
            if (!rmx::parameters[i].advanced)
                continue;
            profile += "param ";
            profile += rmx::parameters[i].id;
            profile += ' ';
            auto numeric = std::to_string(rmx::parameters[i].initial);
            numeric.insert(numeric.front() == '-' ? 1 : 0, 8, '0');
            profile += numeric;
            profile += '\n';
            ++advanced;
        }
        require(profile.size() > 4096 && profile.size() <= rmx::storage::maximumProfileBytes,
                "Full profile test does not exercise streaming");
        TextFile file(profile);
        rmx::storage::Profile decoded;
        require(rmx::storage::decodeProfile(file, rmx::storage::Kind::User, decoded) ==
                    rmx::storage::Error::None,
                "Full User profile rejected");
        size_t loaded = 0;
        for (bool present : decoded.present)
            loaded += present;
        require(loaded == advanced, "Full profile silently omitted settings");
        for (auto p :
             {Param::Bypass, Param::WetOnly, Param::SceneOn, Param::ReleaseAmount, Param::UserSettings})
            require(!rmx::storage::permitted(rmx::storage::Kind::Preset, p),
                    "Card can restore unsafe held state");
        std::cout << "F06: " << rmx::parameterCount << " maintained parameters, " << advanced
                  << " advanced User settings; shared gestures, startup suppression, long/chord actions and "
                     "streaming profiles pass\n";
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
