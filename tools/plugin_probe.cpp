#include <juce_audio_utils/juce_audio_utils.h>
#include "../include/rmx/Parameters.h"
#include "audio_plugin_host.h"
#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <mutex>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#if JUCE_MAC
 #include <AudioToolbox/AudioToolbox.h>
 #include <CoreFoundation/CoreFoundation.h>
#endif

namespace {
struct Check {
    juce::String name;
    bool passed{};
    juce::String detail;
};

using rmx::host::LocalAudioUnit;

// Plugins execute native code. A hung scan/process call must not block the
// invoking terminal indefinitely. This cannot contain a plugin process crash.
class Deadline {
public:
    explicit Deadline(int seconds) : worker([this, seconds] {
        std::unique_lock lock(mutex);
        if (condition.wait_for(lock, std::chrono::seconds(seconds), [this] { return done; })) return;
        std::fprintf(stdout, "{\"kind\":\"plugin-runtime-smoke\",\"passed\":false,\"error\":\"watchdog timeout\",\"last_stage\":%d}\n", stage.load());
        std::fflush(stdout);
        std::_Exit(124);
    }) {}
    ~Deadline() {
        { std::lock_guard lock(mutex); done = true; }
        condition.notify_one();
        worker.join();
    }
    std::atomic<int> stage{};
private:
    std::mutex mutex;
    std::condition_variable condition;
    bool done{};
    std::thread worker;
};

using rmx::host::Playhead;

class Probe {
public:
    Probe(juce::AudioPluginInstance& instance, Deadline& watchdog) : plugin(instance), deadline(watchdog) {
        plugin.setPlayHead(&head);
        const auto format = plugin.getPluginDescription().pluginFormatName;
        for (const auto& info : rmx::parameters) {
            const auto expectedName = juce::String::fromUTF8(info.name.data(), static_cast<int>(info.name.size()));
            const auto id = juce::String::fromUTF8(info.id.data(), static_cast<int>(info.id.size()));
            const auto vst3ID = juce::String(juce::VST3ClientExtensions::convertJuceParameterId(id));
            juce::AudioProcessorParameter* match = nullptr;
            for (int i = 0; i < plugin.getParameters().size(); ++i) {
                auto* hosted = plugin.getHostedParameter(i);
                if (hosted != nullptr && hosted->getName(128) == expectedName &&
                    (format != "VST3" || hosted->getParameterID() == vst3ID)) {
                    if (match != nullptr) throw std::runtime_error("Ambiguous project parameter: " + id.toStdString());
                    match = hosted;
                }
            }
            if (match == nullptr)
                throw std::runtime_error("Missing project parameter id=" + id.toStdString() + " name=" + expectedName.toStdString() +
                    " expectedVST3ID=" + vst3ID.toStdString() + " totalHosted=" + std::to_string(plugin.getParameters().size()));
            projectParameters.push_back(match);
            defaults.push_back(match->getDefaultValue());
        }
        for (int i = 0; i < plugin.getParameters().size(); ++i) {
            auto* parameter = plugin.getParameters()[i];
            if (std::find(projectParameters.begin(), projectParameters.end(), parameter) != projectParameters.end()) continue;
            auto* hosted = plugin.getHostedParameter(i);
            const auto name = parameter->getName(128);
            // JUCE8's VST3 wrapper exposes16*130 MIDI forwarding parameters,
            // with flags=0. They are transport plumbing, not APVTS controls.
            // Sending their extrema would generate MIDI CC changes in RMX.
            const auto id = hosted != nullptr ? hosted->getParameterID().getLargeIntValue() : -1;
            if (format == "VST3" && id >= 0x6d636d00 && id < 0x6d636d00 + 16 * 130 && name.startsWith("MIDI CC "))
                ++midiForwardingParameters;
            else if (format == "VST3" && id == 0x62797073 && name == "Bypass") {
                wrapperBypass = parameter;
            } else throw std::runtime_error("Unclassified hosted parameter id=" +
                (hosted != nullptr ? hosted->getParameterID().toStdString() : "unknown") + " name=" + name.toStdString());
        }
    }
    ~Probe() { plugin.setPlayHead(nullptr); plugin.releaseResources(); }

    void execute() {
        deadline.stage = 3;
        defaultsToPlugin();
        prepare(48000, 128);
        neutral();
        plugin.getStateInformation(initialState);
        require(initialState.getSize() > 0 && initialState.getSize() <= 8 * 1024 * 1024,
                "initial-state", "nonempty state bounded to 8 MiB");
        deadline.stage = 4;
        parameterExtrema();
        deadline.stage = 5;
        modeChecks();
        deadline.stage = 6;
        stateRecall();
        deadline.stage = 7;
        pads();
        deadline.stage = 8;
        transportAndConfigurations();
        deadline.stage = 9;
    }

    bool passed() const {
        return !checks.empty() && std::all_of(checks.begin(), checks.end(), [](const auto& c) { return c.passed; });
    }
    juce::var result() const {
        auto* object = new juce::DynamicObject;
        juce::Array<juce::var> entries;
        for (const auto& c : checks) {
            auto* check = new juce::DynamicObject;
            check->setProperty("name", c.name);
            check->setProperty("passed", c.passed);
            check->setProperty("detail", c.detail);
            entries.add(juce::var(check));
        }
        object->setProperty("checks", entries);
        object->setProperty("passed", passed());
        object->setProperty("processed_blocks", static_cast<juce::int64>(processedBlocks));
        object->setProperty("hosted_parameter_count", plugin.getParameters().size());
        object->setProperty("project_parameter_count", static_cast<int>(projectParameters.size()));
        object->setProperty("excluded_juce_midi_forwarding_parameters", midiForwardingParameters);
        object->setProperty("excluded_wrapper_bypass_parameters", wrapperBypass != nullptr ? 1 : 0);
        object->setProperty("maximum_absolute_output", maximumOutput);
        object->setProperty("latency_samples", plugin.getLatencySamples());
        return juce::var(object);
    }

private:
    juce::AudioPluginInstance& plugin;
    Deadline& deadline;
    Playhead head;
    std::vector<float> defaults;
    std::vector<juce::AudioProcessorParameter*> projectParameters;
    juce::AudioProcessorParameter* wrapperBypass{};
    int midiForwardingParameters{};
    std::vector<Check> checks;
    juce::MemoryBlock initialState;
    double rate{48000}, position{}, maximumOutput{};
    int block{128};
    uint64_t processedBlocks{};
    std::string lastFailure;

    void require(bool condition, juce::String name, juce::String detail) {
        checks.push_back({std::move(name), condition, std::move(detail)});
    }
    juce::AudioProcessorParameter* named(const juce::String& name) const {
        for (auto* p : projectParameters) if (p->getName(128) == name) return p;
        throw std::runtime_error("Required RMX parameter unavailable: " + name.toStdString());
    }
    void value(const juce::String& name, float normalised) {
        named(name)->setValueNotifyingHost(normalised);
    }
    void defaultsToPlugin() {
        for (size_t i = 0; i < projectParameters.size(); ++i) projectParameters[i]->setValueNotifyingHost(defaults[i]);
        if (wrapperBypass != nullptr) wrapperBypass->setValueNotifyingHost(0);
    }
    void prepare(double newRate, int newBlock) {
        plugin.releaseResources();
        rate = newRate;
        block = newBlock;
        position = 0;
        plugin.setRateAndBufferSizeDetails(rate, block);
        plugin.prepareToPlay(rate, block);
        head.locate(position, rate, 120, true);
    }
    void restoreInitial() {
        plugin.setStateInformation(initialState.getData(), static_cast<int>(initialState.getSize()));
        prepare(rate, block);
    }
    bool process(juce::AudioBuffer<float>& audio, juce::MidiBuffer& midi, bool playing = true,
                 double bpm = 120) {
        head.locate(position, rate, bpm, playing);
        plugin.processBlock(audio, midi);
        ++processedBlocks;
        if (playing) position += audio.getNumSamples() / rate;
        for (int channel = 0; channel < audio.getNumChannels(); ++channel)
            for (int i = 0; i < audio.getNumSamples(); ++i) {
                const double sample = audio.getSample(channel, i);
                if (!std::isfinite(sample)) { lastFailure = "non-finite output"; return false; }
                maximumOutput = std::max(maximumOutput, std::abs(sample));
                if (std::abs(sample) > 16) { lastFailure = "absolute output exceeds safety bound 16"; return false; }
            }
        return true;
    }
    bool signalBlocks(int count, bool playing = true, double bpm = 120) {
        juce::AudioBuffer<float> audio(2, block);
        juce::MidiBuffer midi;
        for (int n = 0; n < count; ++n) {
            for (int i = 0; i < block; ++i) {
                const double time = position + i / rate;
                audio.setSample(0, i, static_cast<float>(.1 * std::sin(time * 2 * 3.141592653589793 * 173)));
                audio.setSample(1, i, static_cast<float>(.075 * std::sin(time * 2 * 3.141592653589793 * 431)));
            }
            midi.clear();
            if (!process(audio, midi, playing, bpm)) return false;
        }
        return true;
    }
    void neutral() {
        // The RMX neutral path has zero reported latency. Do not conceal a
        // nontransparent path by searching for a favorable alignment or gain.
        juce::AudioBuffer<float> audio(2, block), expected(2, block);
        juce::MidiBuffer midi;
        double error = 0, energy = 0;
        bool finite = true;
        for (int n = 0; n < 32; ++n) {
            for (int channel = 0; channel < 2; ++channel)
                for (int i = 0; i < block; ++i) {
                    const float sample = static_cast<float>(.1 * std::sin((n * block + i) * (channel ? .071 : .043)));
                    audio.setSample(channel, i, sample);
                    expected.setSample(channel, i, sample);
                }
            midi.clear();
            finite = process(audio, midi) && finite;
            for (int channel = 0; channel < 2; ++channel)
                for (int i = 0; i < block; ++i) {
                    error = std::max(error, std::abs(static_cast<double>(audio.getSample(channel, i) - expected.getSample(channel, i))));
                    energy += audio.getSample(channel, i) * audio.getSample(channel, i);
                }
        }
        require(finite && plugin.getLatencySamples() == 0 && error < 1e-4 && energy > .01,
                "neutral-stereo", "max_absolute_error=" + juce::String(error, 9) + "; zero-latency expectation; nonzero stereo input");
    }
    void parameterExtrema() {
        for (auto* parameter : projectParameters) {
            for (float extreme : {0.f, 1.f}) {
                defaultsToPlugin();
                value("Scene enabled", 1);
                value("Default / User settings", 1);
                parameter->beginChangeGesture();
                parameter->setValueNotifyingHost(extreme);
                parameter->endChangeGesture();
                const float readback = parameter->getValue();
                const bool validValue = std::isfinite(readback) && std::abs(readback - extreme) < 1e-4f;
                const bool finite = signalBlocks(8);
                require(validValue && finite, "parameter-extreme/" + parameter->getName(128) + "/" + juce::String(extreme),
                        "normalized_readback=" + juce::String(readback, 6) + (finite ? "; finite output" : "; " + juce::String(lastFailure)));
            }
        }
    }
    void modeChecks() {
        for (int scene = 0; scene < 10; ++scene) {
            defaultsToPlugin();
            value("Scene enabled", 1);
            value("Scene depth", .85f);
            value("Scene FX", scene / 9.f);
            require(signalBlocks(32), "scene/" + juce::String(scene), "finite processing at active depth");
        }
        for (int mode = 0; mode < 4; ++mode) {
            for (float extreme : {0.f, 1.f}) {
                defaultsToPlugin();
                value("Isolator mode", mode / 3.f);
                for (const auto* band : {"Low", "Mid", "High"}) value(band, extreme);
                require(signalBlocks(32), "isolator/" + juce::String(mode) + "/" + juce::String(extreme), "finite processing at band extrema");
            }
        }
    }
    void stateRecall() {
        defaultsToPlugin();
        value("Output gain", .37f);
        value("Scene FX", 7.f / 9);
        value("Scene enabled", 1);
        signalBlocks(2);
        std::vector<float> saved;
        for (auto* p : projectParameters) saved.push_back(p->getValue());
        juce::MemoryBlock state;
        plugin.getStateInformation(state);
        value("Output gain", .9f);
        value("Scene FX", 0);
        signalBlocks(2);
        plugin.setStateInformation(state.getData(), static_cast<int>(state.getSize()));
        bool match = state.getSize() > 0 && state.getSize() <= 8 * 1024 * 1024;
        for (size_t i = 0; i < projectParameters.size(); ++i) {
            const auto* p = projectParameters[i];
            // The project deliberately clears momentary gestures on recall.
            if (p->getName(128) == "Release lever" || p->getName(128) == "Roll hold") continue;
            match = match && std::isfinite(p->getValue()) && std::abs(p->getValue() - saved[static_cast<size_t>(i)]) < 1e-4;
        }
        require(match && signalBlocks(8), "state-roundtrip", "parameter snapshot restored; momentary gestures excluded; bytes=" + juce::String(static_cast<juce::int64>(state.getSize())));
    }
    void pads() {
        for (int note = 36; note <= 39; ++note) {
            restoreInitial();
            juce::AudioBuffer<float> audio(2, block);
            juce::MidiBuffer midi;
            double energy = 0;
            bool finite = true;
            const int count = static_cast<int>(std::ceil(rate * .6 / block));
            for (int n = 0; n < count; ++n) {
                audio.clear();
                midi.clear();
                // The original factory controller ignores a press before its
                // first processing callback; exercise a warmed-up pad here.
                if (n == 1) midi.addEvent(juce::MidiMessage::noteOn(1, note, static_cast<juce::uint8>(100)), 0);
                if (n == 2) midi.addEvent(juce::MidiMessage::noteOff(1, note), 0);
                finite = process(audio, midi) && finite;
                for (int channel = 0; channel < 2; ++channel)
                    for (int i = 0; i < block; ++i) energy += audio.getSample(channel, i) * audio.getSample(channel, i);
            }
            require(finite && energy > 1e-8, "midi-pad/" + juce::String(note), "silent input, factory note produces energy=" + juce::String(energy, 9));
        }
    }
    void transportAndConfigurations() {
        restoreInitial();
        int configuration = 0;
        for (double sampleRate : {44100., 48000., 88200., 96000.}) {
            for (int frames : {32, 64, 127, 128, 256, 512, 1024}) {
                defaultsToPlugin();
                value("Scene enabled", 1);
                value("Scene depth", .65f);
                value("Scene FX", (configuration % 10) / 9.f);
                value("Isolator mode", ((configuration / 7) % 4) / 3.f);
                value("Low", .8f);
                ++configuration;
                prepare(sampleRate, frames);
                bool finite = signalBlocks(8, true, 120);
                finite = signalBlocks(8, false, 120) && finite;
                position = 64; // Forward host seek while stopped, then play.
                finite = signalBlocks(8, true, 173) && finite;
                position = 0; // Backward host seek.
                finite = signalBlocks(8, true, 90) && finite;
                require(finite, "transport/" + juce::String(sampleRate, 0) + "/" + juce::String(frames),
                        "active Scene/Isolate, play/stop, forward/backward seek, BPM120/173/90; finite output only");
            }
        }
    }
};

juce::var failure(const juce::String& error) {
    auto* report = new juce::DynamicObject;
    report->setProperty("kind", "plugin-runtime-smoke");
    report->setProperty("passed", false);
    report->setProperty("error", error);
    return juce::var(report);
}
} // namespace

int main(int argc, char** argv) {
    try {
        juce::String path;
        int timeout = 120;
        for (int i = 1; i < argc; ++i) {
            const std::string arg = argv[i];
            if (arg == "--timeout-seconds" && i + 1 < argc) timeout = std::stoi(argv[++i]);
            else if (arg == "--help") {
                std::cout << "RMXPluginProbe /absolute/path/RMX.vst3 [--timeout-seconds 120]\n"
                             "Explicit bundle only, no editor or device I/O. Development smoke host, not DAW validation.\n";
                return 0;
            } else if (path.isEmpty()) path = argv[i];
            else throw std::runtime_error("Unexpected argument: " + arg);
        }
        if (path.isEmpty() || timeout < 5 || timeout > 600)
            throw std::runtime_error("Supply a plugin bundle and timeout from 5 to 600 seconds");
        juce::File file = juce::File::getCurrentWorkingDirectory().getChildFile(path);
        if (!file.exists()) throw std::runtime_error("Plugin bundle does not exist: " + file.getFullPathName().toStdString());
        Deadline deadline(timeout);
        juce::ScopedJuceInitialiser_GUI initialise;
        if (!juce::MessageManager::getInstance()->isThisTheMessageThread())
            throw std::runtime_error("Plugin creation must run on the JUCE message thread");
        deadline.stage = 1;
        LocalAudioUnit localAU(file);
        juce::AudioPluginFormatManager formats;
        formats.addDefaultFormats();
        juce::OwnedArray<juce::PluginDescription> descriptions;
        for (auto* format : formats.getFormats())
            if (format->fileMightContainThisPluginType(file.getFullPathName()))
                format->findAllTypesForFile(descriptions, file.getFullPathName());
        if (descriptions.size() != 1)
            throw std::runtime_error("Expected one plugin type from explicit bundle; found " + std::to_string(descriptions.size()));
        if (!descriptions[0]->name.containsIgnoreCase("RMX"))
            throw std::runtime_error("This probe expects the RMX parameter contract");
        deadline.stage = 2;
        juce::String error;
        auto plugin = formats.createPluginInstance(*descriptions[0], 48000, 128, error);
        if (!plugin) throw std::runtime_error("Plugin creation failed: " + error.toStdString());
        auto buses = plugin->getBusesLayout();
        if (buses.inputBuses.isEmpty() || buses.outputBuses.isEmpty())
            throw std::runtime_error("Plugin has no stereo input/output buses");
        buses.inputBuses.getReference(0) = juce::AudioChannelSet::stereo();
        buses.outputBuses.getReference(0) = juce::AudioChannelSet::stereo();
        if (!plugin->setBusesLayout(buses) || plugin->getTotalNumInputChannels() != 2 || plugin->getTotalNumOutputChannels() != 2)
            throw std::runtime_error("Could not configure stereo input/output");
        Probe probe(*plugin, deadline);
        probe.execute();
        auto report = probe.result();
        auto* object = report.getDynamicObject();
        object->setProperty("kind", "plugin-runtime-smoke");
        object->setProperty("plugin_path", file.getFullPathName());
        object->setProperty("plugin_format", descriptions[0]->pluginFormatName);
        object->setProperty("plugin_version", descriptions[0]->version);
        object->setProperty("process_local_au_registration", localAU.registered);
        if (localAU.registered) {
            object->setProperty("au_factory_function", localAU.factory);
            object->setProperty("visible_audio_components_before_registration", static_cast<int>(localAU.visibleComponentsBefore));
        }
        object->setProperty("editor_created", false);
        object->setProperty("limitations", "No real DAW, GUI, device I/O, user sample recall, physical controller, long-session or sonic parity validation. A plugin crash can terminate this process before JSON is written.");
        std::cout << juce::JSON::toString(report).toStdString() << std::endl;
        return probe.passed() ? 0 : 2;
    } catch (const std::exception& error) {
        std::cout << juce::JSON::toString(failure(error.what())).toStdString() << std::endl;
        return 1;
    }
}
