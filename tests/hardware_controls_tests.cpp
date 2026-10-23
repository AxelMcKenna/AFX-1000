#include "rmx/HardwareControls.h"
#include <iostream>
#include <stdexcept>

namespace {
void require(bool v, const char* message) {
    if (!v)
        throw std::runtime_error(message);
}
} // namespace
int main() {
    try {
        using namespace rmx;
        using namespace rmx::hardware;
        Engine engine;
        auto bank = makeFactoryBank();
        engine.setBank(&bank);
        engine.prepare(48000, 128);
        Controls controls(engine);
        std::array<float, 128> l{}, r{};
        auto process = [&] { engine.process(nullptr, nullptr, l.data(), r.data(), 128); };
        uint32_t now = 100;
        auto click = [&](Button id) {
            controls.button(id, true, now);
            controls.button(id, false, now + 20);
            now += 30;
        };
        controls.knob(Knob::Input, .5);
        controls.knob(Knob::Output, .5);
        require(engine.params.get(Param::InputGain) == 0 && engine.params.get(Param::OutputGain) == 0,
                "Physical center must be unity gain");
        controls.knob(Knob::Low, .508);
        require(engine.params.get(Param::Low) == 0, "Detent center must be neutral");
        controls.knob(Knob::SceneDepth, .6);
        require(engine.params.get(Param::SceneOn) == 0, "Boot depth read engaged Scene FX");
        controls.knob(Knob::SceneDepth, .61);
        require(engine.params.get(Param::SceneOn) == 1, "Depth motion failed to enable Scene FX");
        click(Button::Scene9);
        require(engine.params.get(Param::SceneType) == 9 && engine.params.get(Param::SceneOn) == 1,
                "Scene button mapping failed");
        click(Button::Scene9);
        require(engine.params.get(Param::SceneOn) == 0, "Repeated scene press did not bypass");
        click(Button::InputSource);
        require(engine.params.get(Param::SceneSource) == 1, "Input source bit failed");
        click(Button::PadSource);
        require(engine.params.get(Param::SceneSource) == 3, "Both sources off encoding failed");
        click(Button::InputSource);
        require(engine.params.get(Param::SceneSource) == 0, "Input-only encoding failed");
        click(Button::PadSource);
        require(engine.params.get(Param::IsolateSource) == 2, "Source routing did not restore both sections");
        engine.params.set(Param::AutoTempo, 1);
        click(Button::NudgeUp);
        require(engine.params.get(Param::AutoTempo) == 0 &&
                    std::abs(engine.params.get(Param::Tempo) - 120.1f) < .001,
                "Nudge failed");
        for (int i = 0; i < 4; ++i)
            click(Button::Bank);
        require(engine.params.get(Param::Bank) == 0, "Bank cycle failed");
        require(controls.releaseSelection(false, false) && engine.params.get(Param::ReleaseType) == 1,
                "Release selector center is not Echo");
        require(!controls.releaseSelection(true, true) && engine.params.get(Param::ReleaseType) == 1,
                "Invalid selector changed Release FX");
        click(Button::Scene1);
        process();
        controls.release(1);
        process();
        controls.release(0);
        process();
        require(engine.params.get(Param::SceneOn) == 0, "Physical lever return failed to reset FX");
        controls.knob(Knob::SceneDepth, .61);
        require(engine.params.get(Param::SceneOn) == 0, "Unmoved depth re-enabled FX after release");
        controls.release(1);
        controls.release(.5, false);
        require(engine.params.get(Param::ReleaseAmount) == 0, "Invalid lever sensor left release engaged");
        click(Button::Overdub);
        require(engine.params.get(Param::Overdub) == 1, "Short Overdub action failed");
        controls.button(Button::Overdub, true, now);
        controls.tick(now + 701);
        controls.button(Button::Overdub, false, now + 720);
        require(engine.params.get(Param::Overdub) == 0, "Long Overdub must clear and stop recording");
        now += 1000;
        controls.button(Button::Hold, true, now);
        controls.tick(now + 701);
        controls.button(Button::Hold, false, now + 720);
        require(engine.params.get(Param::SamplerMute) == 1 && engine.params.get(Param::XHold) == 0,
                "Long Hold must mute without toggling Hold");
        engine.params.set(Param::SamplerMute, 0);
        engine.params.set(Param::Quantize, 0);
        click(Button::Pad3);
        controls.touch(1, true);
        process();
        require(engine.params.get(Param::XRoll) == 7, "Right touch endpoint is not final zone");
        double energy = 0;
        for (int i = 0; i < 150; ++i) {
            process();
            for (float v : l)
                energy += v * v;
        }
        require(energy > .01, "Physical pad/touch pipeline is silent");
        click(Button::Hold);
        controls.touch(0, false);
        process();
        require(engine.params.get(Param::XHold) == 1, "Hold did not latch");
        click(Button::Hold);
        process();
        require(engine.params.get(Param::XHold) == 0, "Hold off failed");
        controls.initializeButtons(uint32_t(1) << static_cast<unsigned>(Button::Overdub));
        controls.button(Button::Overdub, false, now);
        require(engine.params.get(Param::Overdub) == 0, "Held boot key fired on release");
        const auto led = controls.feedback(now);
        require(led.size() == 96 && led[65] == 4095, "Bank feedback failed");
        require(led[69] == 0 && led[70] == 4095 && led[71] == 4095, "BPM hundreds digit is not one");
        Debouncer debounce;
        debounce.begin(0);
        require(debounce.update(1, 100) == 0 && debounce.update(0, 102) == 0 && debounce.update(1, 104) == 0,
                "Bounce produced an edge");
        require(debounce.update(1, 108) == 0 && debounce.update(1, 109) == 1 && debounce.state() == 1,
                "Stable key did not debounce");
        debounce.begin(0);
        debounce.update(1, 0xfffffffd);
        require(debounce.update(1, 3) == 1, "Debounce timer failed across wrap");
        std::cout << "Hardware control behavior, audio dispatch, feedback and debounce checks passed\n";
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
