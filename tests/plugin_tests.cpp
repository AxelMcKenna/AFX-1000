#include "../src/plugin/RMXProcessor.h"
#include "TestSupport.h"

namespace {
struct Listener : juce::AudioProcessorParameter::Listener {
    float last{-1};
    void parameterValueChanged(int, float value) override {
        last = value;
    }
    void parameterGestureChanged(int, bool) override {}
};
} // namespace
int main() {
    juce::ScopedJuceInitialiser_GUI juce;
    return runTests([] {
        RMXProcessor processor;
        processor.setRateAndBufferSizeDetails(48000, 128);
        processor.prepareToPlay(48000, 128);
        juce::AudioBuffer<float> buffer(2, 128);
        juce::MidiBuffer midi;
        auto block = [&] {
            buffer.clear();
            processor.processBlock(buffer, midi);
        };
        auto set = [&](rmx::Param p, float value) {
            auto* parameter = processor.parameter(p);
            parameter->setValueNotifyingHost(parameter->convertTo0to1(value));
        };
        Listener sceneListener;
        processor.parameter(rmx::Param::SceneOn)->addListener(&sceneListener);
        set(rmx::Param::SceneOn, 1);
        set(rmx::Param::Low, .7f);
        set(rmx::Param::ReleaseAmount, 1);
        block();
        processor.engine.enqueue({rmx::EventType::Panic});
        block();
        for (int i = 0; i < 20; ++i)
            block(); // No message-thread timer/acknowledgment.
        require(processor.value(rmx::Param::SceneOn) == 0 && processor.value(rmx::Param::Low) == 0 &&
                    processor.value(rmx::Param::ReleaseAmount) == 0,
                "Host values resurrected effects after panic");
        require(processor.parameter(rmx::Param::ReleaseAmount)->getValue() == 0,
                "Host did not immediately observe release reset");
        set(rmx::Param::SceneOn, 1); // New automation supersedes unnotified panic.
        processor.notifyParameterChanges();
        block();
        require(processor.value(rmx::Param::SceneOn) == 1 && sceneListener.last == 1,
                "Deferred notification overwrote newer automation");
        set(rmx::Param::ReleaseAmount, 1);
        block();
        set(rmx::Param::ReleaseAmount, 0);
        block();
        for (int i = 0; i < 20; ++i)
            block();
        require(processor.value(rmx::Param::SceneOn) == 0, "Release reset was reverted on the next callback");
        processor.notifyParameterChanges();
        require(sceneListener.last == 0, "Audio-generated reset did not reach host listeners");
        set(rmx::Param::SceneDepth, .35f);
        midi.addEvent(juce::MidiMessage::controllerEvent(1, 16, 45), 0);
        block();
        midi.addEvent(juce::MidiMessage::controllerEvent(1, 16, 100), 0);
        block();
        const auto depth = processor.value(rmx::Param::SceneDepth);
        for (int i = 0; i < 20; ++i)
            block();
        require(depth > .7f && processor.value(rmx::Param::SceneDepth) == depth,
                "MIDI control was overwritten before host notification");
        juce::MemoryBlock saved;
        processor.getStateInformation(saved);
        set(rmx::Param::SceneDepth, 0);
        processor.setStateInformation(saved.getData(), static_cast<int>(saved.getSize()));
        require(processor.value(rmx::Param::SceneDepth) == depth,
                "Host serialization lost authoritative engine state");
        processor.parameter(rmx::Param::SceneOn)->removeListener(&sceneListener);
    });
}
