#pragma once
#include "EngineParameter.h"
#include "rmx/Engine.h"
#include "rmx/MidiControls.h"
#include "rmx/State.h"
#include "rmx/Wav.h"
#include <juce_audio_utils/juce_audio_utils.h>
#include <memory>

class RMXProcessor final : public juce::AudioProcessor, private juce::Timer {
  public:
    rmx::Engine engine;
    juce::String assetMessage;
    RMXProcessor();
    ~RMXProcessor() override;
    const juce::String getName() const override {
        return "RMX";
    }
    bool acceptsMidi() const override {
        return true;
    }
    bool producesMidi() const override {
        return false;
    }
    bool isMidiEffect() const override {
        return false;
    }
    double getTailLengthSeconds() const override;
    int getNumPrograms() override {
        return 1;
    }
    int getCurrentProgram() override {
        return 0;
    }
    void setCurrentProgram(int) override {}
    const juce::String getProgramName(int) override {
        return "Performance";
    }
    void changeProgramName(int, const juce::String&) override {}
    bool hasEditor() const override {
        return true;
    }
    juce::AudioProcessorEditor* createEditor() override;
    bool isBusesLayoutSupported(const BusesLayout& b) const override {
        return b.getMainInputChannelSet() == juce::AudioChannelSet::stereo() &&
               b.getMainOutputChannelSet() == juce::AudioChannelSet::stereo();
    }
    void prepareToPlay(double rate, int block) override;
    void releaseResources() override {}
    void processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midi) override;
    void getStateInformation(juce::MemoryBlock& destination) override;
    void setStateInformation(const void* data, int bytes) override;
    void change(rmx::Param p, float value);
    void importSample(int slot, const juce::File& file);
    void save(const juce::File& file);
    void load(const juce::File& file);

    juce::RangedAudioParameter* parameter(rmx::Param p) const {
        return hostParameters[static_cast<size_t>(p)];
    }
    float value(rmx::Param p) const {
        return engine.params.get(p);
    }
    // Message-thread notification only: never replay an older value into the store.
    void notifyParameterChanges();

  private:
    rmx::State state;
    struct Assets {
        rmx::SampleBank bank;
        uint64_t generation;
    };
    std::vector<std::unique_ptr<Assets>> owned;
    std::atomic<const Assets*> published{};
    std::atomic<uint64_t> acknowledged{};
    uint64_t generation{};
    juce::CriticalSection assetLock;
    std::array<EngineParameter*, rmx::parameterCount> hostParameters{};
    std::array<float, rmx::parameterCount> lastNotified{};
    rmx::MidiControls midiControls;
    uint64_t sampleClock{};
    void publish(rmx::SampleBank bank);
    void restore(rmx::State next);

    void timerCallback() override;
};
