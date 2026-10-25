#pragma once
#include <juce_audio_utils/juce_audio_utils.h>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <vector>
#if JUCE_MAC
 #include <CoreFoundation/CoreFoundation.h>
#endif

// Original, minimal offline host adapter for the public VST 2.4 binary ABI.
// Interoperability layouts/opcodes were checked against the RustAudio/vst-rs
// implementation (src/api.rs, src/host.rs, src/plugin.rs). No Steinberg SDK or
// manufacturer implementation is included. Only one explicit instance is hosted.
// https://github.com/RustAudio/vst-rs/tree/master/src
namespace rmx::host {
namespace vst2 {
struct Effect;
using Callback = intptr_t (*)(Effect*, int32_t, int32_t, intptr_t, void*, float);
using Process = void (*)(Effect*, float**, float**, int32_t);
struct Effect {
    int32_t magic;
    Callback dispatch;
    Process accumulating;
    void (*setParameter)(Effect*, int32_t, float);
    float (*getParameter)(Effect*, int32_t);
    int32_t programs, parameters, inputs, outputs, flags;
    intptr_t reserved1, reserved2;
    int32_t latency, obsolete1, obsolete2;
    float obsoleteRatio;
    void *object, *user;
    int32_t identifier, version;
    Process replacing;
    void (*doubleReplacing)(Effect*, double**, double**, int32_t);
    char future[56];
};
struct Time {
    double samples{}, rate{48000}, nanoseconds{}, quarters{}, tempo{120}, bar{}, cycleStart{}, cycleEnd{};
    int32_t numerator{4}, denominator{4}, smpteOffset{}, smpteRate{}, nextClock{}, flags{};
};
struct Midi {
    int32_t type{1}, bytes{32}, offset{}, flags{}, length{}, noteOffset{};
    uint8_t data[4]{};
    int8_t detune{};
    uint8_t releaseVelocity{}, reserved1{}, reserved2{};
};
struct Events {
    int32_t count{};
    intptr_t reserved{};
    Midi* messages[1024]{};
};
static_assert(sizeof(Effect) == 192 && offsetof(Effect, replacing) == 120);
static_assert(sizeof(Time) == 88 && sizeof(Midi) == 32 && offsetof(Events, messages) == 16);
}

#if JUCE_MAC
class LegacyVST2 final : public juce::AudioPluginInstance {
public:
    explicit LegacyVST2(const juce::File& file, double rate, int block)
        : AudioPluginInstance(BusesProperties().withInput("Input", juce::AudioChannelSet::stereo(), true)
            .withOutput("Output", juce::AudioChannelSet::stereo(), true)), bundleFile(file), maximumBlock(block) {
        LegacyVST2* empty = nullptr;
        check(active.compare_exchange_strong(empty, this), "Only one legacy VST2 instance may be hosted per process");
        time.rate = rate;
        try {
            const auto text = file.getFullPathName().toUTF8();
            auto url = CFURLCreateFromFileSystemRepresentation(nullptr,
                reinterpret_cast<const UInt8*>(text.getAddress()), static_cast<CFIndex>(text.sizeInBytes() - 1), true);
            check(url != nullptr, "Cannot form VST2 bundle URL");
            bundle = CFBundleCreate(nullptr, url);
            CFRelease(url);
            check(bundle != nullptr, "Cannot read VST2 bundle");
            CFErrorRef error = nullptr;
            if (!CFBundleLoadExecutableAndReturnError(bundle, &error)) {
                juce::String detail;
                if (error != nullptr) {
                    auto description = CFErrorCopyDescription(error);
                    detail = juce::String::fromCFString(description);
                    CFRelease(description); CFRelease(error);
                }
                throw std::runtime_error(("Cannot load VST2 executable; match the host architecture: " + detail).toStdString());
            }
            using Entry = vst2::Effect* (*)(vst2::Callback);
            auto entry = reinterpret_cast<Entry>(CFBundleGetFunctionPointerForName(bundle, CFSTR("VSTPluginMain")));
            if (entry == nullptr) entry = reinterpret_cast<Entry>(CFBundleGetFunctionPointerForName(bundle, CFSTR("main_macho")));
            check(entry != nullptr, "Explicit bundle exports no VST2 entry point");
            effect = entry(callback);
            check(effect != nullptr && effect->magic == 0x56737450 && effect->dispatch != nullptr,
                "Invalid VST2 effect interface");
            validInterface = true;
            check(effect->replacing != nullptr && (effect->flags & (1 << 4)) != 0,
                "VST2 reference must support float replacing processing");
            check(effect->inputs == 2 && effect->outputs == 2 && effect->parameters >= 0 && effect->parameters <= 4096,
                "VST2 reference must be stereo with a bounded parameter list");
            check(effect->setParameter != nullptr && effect->getParameter != nullptr, "Missing VST2 parameter interface");
            dispatch(0);
            opened = true;
            description.name = stringOpcode(45);
            description.manufacturerName = stringOpcode(47);
            description.pluginFormatName = "VST2";
            description.fileOrIdentifier = file.getFullPathName();
            description.uniqueId = effect->identifier;
            description.numInputChannels = effect->inputs;
            description.numOutputChannels = effect->outputs;
            description.isInstrument = (effect->flags & (1 << 8)) != 0;
            const auto version = CFBundleGetValueForInfoDictionaryKey(bundle, CFSTR("CFBundleShortVersionString"));
            description.version = version != nullptr && CFGetTypeID(version) == CFStringGetTypeID()
                ? juce::String::fromCFString(static_cast<CFStringRef>(version)) : juce::String(effect->version);
            check(description.name.isNotEmpty() && description.manufacturerName.isNotEmpty(), "Missing VST2 vendor/effect identity");
            midiInput = dispatch(51, 0, 0, const_cast<char*>("receiveVstMidiEvent")) > 0;
            for (int i = 0; i < effect->parameters; ++i) {
                const auto value = effect->getParameter(effect, i);
                check(std::isfinite(value) && value >= 0 && value <= 1, "Invalid VST2 initial parameter value");
                addHostedParameter(std::make_unique<Parameter>(*this, i, value));
            }
            setLatencySamples(std::max(0, effect->latency));
        } catch (...) {
            close();
            throw;
        }
    }
    ~LegacyVST2() override { close(); }
    const juce::String getName() const override { return description.name; }
    void fillInPluginDescription(juce::PluginDescription& result) const override { result = description; }
    void prepareToPlay(double rate, int block) override {
        releaseResources();
        time.rate = rate;
        maximumBlock = block;
        input.setSize(2, block);
        setRateAndBufferSizeDetails(rate, block);
        dispatch(10, 0, 0, nullptr, static_cast<float>(rate));
        dispatch(11, 0, block);
        dispatch(77, 0, 0); // float precision
        dispatch(12, 0, 1);
        dispatch(71);
        running = true;
        setLatencySamples(std::max(0, effect->latency));
    }
    void releaseResources() override {
        if (running && effect != nullptr) { dispatch(72); dispatch(12, 0, 0); running = false; }
    }
    void reset() override {
        if (running) { dispatch(12, 0, 0); dispatch(12, 0, 1); }
    }
    bool isBusesLayoutSupported(const BusesLayout& layout) const override {
        return layout.getMainInputChannelSet() == juce::AudioChannelSet::stereo()
            && layout.getMainOutputChannelSet() == juce::AudioChannelSet::stereo();
    }
    void processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midi) override {
        const auto frames = buffer.getNumSamples();
        check(running && frames <= maximumBlock && effect->inputs == 2 && effect->outputs == 2, "VST2 processing layout changed");
        if (auto* playhead = getPlayHead()) if (auto position = playhead->getPosition()) {
            time.samples = static_cast<double>(position->getTimeInSamples().orFallback(0));
            time.quarters = position->getPpqPosition().orFallback(time.samples / time.rate * 2);
            time.tempo = position->getBpm().orFallback(120);
            time.bar = position->getPpqPositionOfLastBarStart().orFallback(std::floor(time.quarters / 4) * 4);
            time.flags = (1 << 9) | (1 << 10) | (1 << 11) | (1 << 13)
                | (position->getIsPlaying() ? (1 << 1) : 0);
            if (time.samples == 0) time.flags |= 1;
        }
        std::vector<vst2::Midi> messages;
        messages.reserve(static_cast<size_t>(midi.getNumEvents()));
        for (const auto metadata : midi) {
            check(metadata.numBytes >= 1 && metadata.numBytes <= 3 && messages.size() < 1024,
                "Legacy VST2 adapter supports at most 1024 short MIDI messages per block");
            vst2::Midi event;
            event.offset = metadata.samplePosition;
            std::memcpy(event.data, metadata.data, static_cast<size_t>(metadata.numBytes));
            messages.push_back(event);
        }
        if (!messages.empty()) {
            vst2::Events events;
            events.count = static_cast<int32_t>(messages.size());
            for (size_t i = 0; i < messages.size(); ++i) events.messages[i] = &messages[i];
            dispatch(25, 0, 0, &events);
        }
        for (int ch = 0; ch < 2; ++ch) input.copyFrom(ch, 0, buffer, ch, 0, frames);
        float* inputs[]{input.getWritePointer(0), input.getWritePointer(1)};
        float* outputs[]{buffer.getWritePointer(0), buffer.getWritePointer(1)};
        effect->replacing(effect, inputs, outputs, frames);
        midi.clear();
    }
    double getTailLengthSeconds() const override {
        const auto samples = dispatch(52);
        return samples > 1 && samples < INT32_MAX ? static_cast<double>(samples) / time.rate : 0;
    }
    bool acceptsMidi() const override { return midiInput; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    bool hasEditor() const override { return false; }
    juce::AudioProcessorEditor* createEditor() override { return nullptr; }
    int getNumPrograms() override { return std::max(1, effect->programs); }
    int getCurrentProgram() override { return static_cast<int>(dispatch(3)); }
    void setCurrentProgram(int program) override { dispatch(2, 0, program); }
    const juce::String getProgramName(int) override { return {}; }
    void changeProgramName(int, const juce::String&) override {}
    void getStateInformation(juce::MemoryBlock& result) override {
        check((effect->flags & (1 << 5)) != 0, "VST2 reference does not expose a complete native state chunk");
        void* data = nullptr;
        const auto bytes = dispatch(23, 0, 0, &data);
        check(bytes > 0 && bytes <= 64 * 1024 * 1024 && data != nullptr, "Invalid/oversized VST2 native state chunk");
        result.replaceAll(data, static_cast<size_t>(bytes));
    }
    void setStateInformation(const void* data, int bytes) override {
        check(data != nullptr && bytes > 0 && bytes <= 64 * 1024 * 1024 && (effect->flags & (1 << 5)), "Invalid VST2 state input");
        dispatch(24, 0, bytes, const_cast<void*>(data));
    }
private:
    struct Parameter final : juce::HostedAudioProcessorParameter {
        LegacyVST2& owner;
        const int index;
        const float initial;
        Parameter(LegacyVST2& instance, int parameter, float value) : owner(instance), index(parameter), initial(value) {}
        float getValue() const override { return owner.effect->getParameter(owner.effect, index); }
        void setValue(float value) override { owner.effect->setParameter(owner.effect, index, value); }
        float getDefaultValue() const override { return initial; }
        juce::String getName(int maximum) const override { return owner.stringOpcode(8, index).substring(0, maximum); }
        juce::String getLabel() const override { return owner.stringOpcode(6, index); }
        juce::String getParameterID() const override { return juce::String(index); }
        juce::String getText(float value, int maximum) const override {
            // VST2 exposes only the current display. Never change a parameter
            // merely to format a hypothetical value during capture.
            return value == getValue() ? owner.stringOpcode(7, index).substring(0, maximum)
                                      : juce::String(value, 7).substring(0, maximum);
        }
        float getValueForText(const juce::String& text) const override { return juce::jlimit(0.f, 1.f, text.getFloatValue()); }
        bool isAutomatable() const override { return owner.dispatch(26, index) > 0; }
    };
    static inline std::atomic<LegacyVST2*> active{};
    CFBundleRef bundle{};
    vst2::Effect* effect{};
    juce::File bundleFile;
    juce::PluginDescription description;
    juce::AudioBuffer<float> input;
    vst2::Time time;
    int maximumBlock{};
    bool opened{}, validInterface{}, running{}, midiInput{};
    static void check(bool valid, const char* message) { if (!valid) throw std::runtime_error(message); }
    intptr_t dispatch(int32_t opcode, int32_t index = 0, intptr_t value = 0, void* pointer = nullptr, float option = 0) const {
        return effect->dispatch(effect, opcode, index, value, pointer, option);
    }
    juce::String stringOpcode(int opcode, int index = 0) const {
        char text[256]{};
        dispatch(opcode, index, 0, text);
        text[255] = 0;
        return juce::String::fromUTF8(text);
    }
    static intptr_t callback(vst2::Effect*, int32_t opcode, int32_t, intptr_t, void* pointer, float) noexcept {
        auto* instance = active.load();
        if (instance == nullptr) return 0;
        switch (opcode) {
            case 0: case 3: case 6: case 42: case 43: case 44: return 1;
            case 1: return 2400;
            case 7: return reinterpret_cast<intptr_t>(&instance->time);
            case 13: return instance->effect != nullptr && instance->effect->inputs == 2 && instance->effect->outputs == 2 ? 1 : 0;
            case 16: return static_cast<intptr_t>(instance->time.rate);
            case 17: return instance->maximumBlock;
            case 23: return 4; // offline processing
            case 24: return 1; // read automation
            case 32: case 33:
                if (pointer != nullptr) std::strcpy(static_cast<char*>(pointer), "AFX Reference Host");
                return 1;
            case 34: return 1;
            case 37:
                if (pointer != nullptr) {
                    const auto* feature = static_cast<const char*>(pointer);
                    return std::strcmp(feature, "sendVstEvents") == 0 || std::strcmp(feature, "sendVstMidiEvent") == 0
                        || std::strcmp(feature, "sendVstTimeInfo") == 0 ? 1 : 0;
                }
                return 0;
            case 38: return 1; // English
            default: return 0;
        }
    }
    void close() noexcept {
        if (effect != nullptr && validInterface) {
            if (running) { dispatch(72); dispatch(12, 0, 0); }
            if (opened) dispatch(1);
        }
        running = opened = false;
        effect = nullptr;
        active.store(nullptr);
        if (bundle != nullptr) { CFRelease(bundle); bundle = nullptr; }
    }
};
#endif
}
