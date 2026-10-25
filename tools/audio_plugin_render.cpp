#include "audio_plugin_host.h"
#include "legacy_vst2_host.h"
#include <juce_cryptography/juce_cryptography.h>
#include <algorithm>
#include <chrono>
#include <condition_variable>
#include <filesystem>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>
#if JUCE_MAC
 #include <mach-o/dyld.h>
#endif

namespace {
using juce::String;
using juce::var;

class Deadline {
public:
    explicit Deadline(int seconds) : worker([this, seconds] {
        std::unique_lock lock(mutex);
        if (!condition.wait_for(lock, std::chrono::seconds(seconds), [this] { return done; })) {
            std::cerr << "Reference host watchdog expired; capture is incomplete\n";
            std::_Exit(124);
        }
    }) {}
    ~Deadline() {
        { std::lock_guard lock(mutex); done = true; }
        condition.notify_one();
        worker.join();
    }
private:
    std::mutex mutex;
    std::condition_variable condition;
    bool done{};
    std::thread worker;
};

var object(std::initializer_list<std::pair<juce::Identifier, var>> properties) {
    auto* result = new juce::DynamicObject;
    for (const auto& [key, value] : properties) result->setProperty(key, value);
    return result;
}

void require(bool condition, const String& message) {
    if (!condition) throw std::runtime_error(message.toStdString());
}

const var& field(const var& value, const juce::Identifier& name) {
    require(value.isObject() && value.hasProperty(name), "Missing field: " + name.toString());
    return value[name];
}

double number(const var& value, const String& name) {
    require(value.isInt() || value.isInt64() || value.isDouble(), name + " must be numeric");
    const double result = static_cast<double>(value);
    require(std::isfinite(result), name + " must be finite");
    return result;
}

int64_t integer(const var& value, const String& name) {
    const auto result = number(value, name);
    require(result == std::floor(result) && std::abs(result) < 9007199254740992., name + " must be an exact integer");
    return static_cast<int64_t>(result);
}

var readJSON(const juce::File& file) {
    require(file.existsAsFile() && file.getSize() <= 4 * 1024 * 1024, "Missing/oversized JSON plan");
    var result;
    const auto status = juce::JSON::parse(file.loadFileAsString(), result);
    require(status.wasOk() && result.isObject(), "Invalid JSON object: " + status.getErrorMessage());
    return result;
}

String parameterID(juce::AudioProcessorParameter& parameter) {
    if (auto* hosted = dynamic_cast<juce::HostedAudioProcessorParameter*>(&parameter)) return hosted->getParameterID();
    if (auto* identified = dynamic_cast<juce::AudioProcessorParameterWithID*>(&parameter)) return identified->paramID;
    throw std::runtime_error("Hosted parameter has no public identifier");
}

var inventory(juce::AudioPluginInstance& plugin, const juce::PluginDescription& description,
              const juce::File& bundle, const String& registeredIdentifier = {}) {
    juce::Array<var> parameters, files;
    int index = 0;
    for (auto* parameter : plugin.getParameters()) {
        parameters.add(object({{"index", index++}, {"id", parameterID(*parameter)},
            {"name", parameter->getName(256)}, {"value", parameter->getValue()},
            {"default", parameter->getDefaultValue()}, {"steps", parameter->getNumSteps()},
            {"text", parameter->getText(parameter->getValue(), 256)}, {"automatable", parameter->isAutomatable()}}));
    }
    juce::Array<juce::File> members;
    if (bundle.isDirectory()) bundle.findChildFiles(members, juce::File::findFiles, true);
    else members.add(bundle);
    std::sort(members.begin(), members.end(), [](const auto& a, const auto& b) {
        return a.getFullPathName() < b.getFullPathName();
    });
    for (const auto& file : members) {
        files.add(object({{"path", file.getRelativePathFrom(bundle.isDirectory() ? bundle : bundle.getParentDirectory())},
            {"bytes", file.getSize()}, {"sha256", juce::SHA256(file).toHexString()}}));
    }
    return object({{"kind", "audio-plugin-inventory"}, {"name", description.name},
        {"manufacturer", description.manufacturerName}, {"version", description.version},
        {"format", description.pluginFormatName}, {"bundle", bundle.getFullPathName()},
        {"discovery_mode", registeredIdentifier.isEmpty() ? "explicit_bundle" : "registered_legacy_au"},
        {"registered_identifier", registeredIdentifier},
        {"binary_files", files}, {"parameters", parameters}});
}

void verifyRegisteredBundleLoaded(const juce::File& bundle) {
   #if JUCE_MAC
    const auto text = bundle.getFullPathName().toUTF8();
    const auto url = CFURLCreateFromFileSystemRepresentation(nullptr,
        reinterpret_cast<const UInt8*>(text.getAddress()), static_cast<CFIndex>(text.sizeInBytes() - 1), true);
    require(url != nullptr, "Cannot form registered AU bundle URL");
    const auto metadata = CFBundleCreate(nullptr, url);
    CFRelease(url);
    require(metadata != nullptr, "Cannot read registered AU bundle metadata");
    const auto executableURL = CFBundleCopyExecutableURL(metadata);
    CFRelease(metadata);
    require(executableURL != nullptr, "Cannot find registered AU executable");
    const auto executablePath = CFURLCopyFileSystemPath(executableURL, kCFURLPOSIXPathStyle);
    CFRelease(executableURL);
    require(executablePath != nullptr, "Cannot read registered AU executable path");
    const auto expected = std::filesystem::canonical(String::fromCFString(executablePath).toStdString());
    CFRelease(executablePath);
    bool found = false;
    for (uint32_t i = 0; i < _dyld_image_count(); ++i) {
        const auto* path = _dyld_get_image_name(i);
        if (path != nullptr) {
            std::error_code error;
            const auto actual = std::filesystem::canonical(path, error);
            if (!error && actual == expected) found = true;
        }
    }
    require(found, "Registered Audio Unit did not load the explicitly supplied bundle executable");
   #else
    (void)bundle;
    throw std::runtime_error("Registered Audio Units require macOS");
   #endif
}

void saveJSON(const juce::File& file, const var& data) {
    require(!file.exists(), "Output already exists: " + file.getFullPathName());
    require(file.replaceWithText(juce::JSON::toString(data, false) + "\n"), "Cannot write JSON output");
}

juce::AudioProcessorParameter& selectParameter(juce::AudioPluginInstance& plugin, const var& setting) {
    const auto index = integer(field(setting, "index"), "parameter index");
    require(index >= 0 && index < plugin.getParameters().size(), "Parameter index outside inventory");
    auto* parameter = plugin.getParameters()[static_cast<int>(index)];
    require(field(setting, "id").toString() == parameterID(*parameter)
        && field(setting, "name").toString() == parameter->getName(256),
        "Parameter index/id/name differs from inventory; refusing an ambiguous mapping");
    const auto value = number(field(setting, "value"), "normalized parameter value");
    require(value >= 0 && value <= 1, "Parameter value must be normalized to 0..1");
    return *parameter;
}

float setParameter(juce::AudioPluginInstance& plugin, const var& setting) {
    auto& parameter = selectParameter(plugin, setting);
    parameter.setValueNotifyingHost(static_cast<float>(number(setting["value"], "parameter value")));
    return parameter.getValue();
}

void render(juce::AudioPluginInstance& plugin, const juce::PluginDescription& description,
            const juce::File& bundle, const juce::File& input, const juce::File& planFile,
            const juce::File& destination, int block, const String& registeredIdentifier) {
    const auto plan = readJSON(planFile);
    const auto planHash = juce::SHA256(planFile).toHexString();
    const auto inputHash = juce::SHA256(input).toHexString();
    require(integer(field(plan, "schema_version"), "schema version") == 1
        && field(plan, "kind").toString() == "audio-plugin-capture-plan", "Unsupported capture plan");
    const auto expected = field(plan, "expected_plugin");
    require(field(expected, "name").toString() == description.name
        && field(expected, "manufacturer").toString() == description.manufacturerName
        && field(expected, "version").toString() == description.version,
        "Plugin name/manufacturer/version differs from capture plan");
    const auto role = field(plan, "role").toString();
    require(role == "reference" || role == "candidate" || role == "host_fixture", "Unknown capture role");
    const auto bpm = number(field(plan, "bpm"), "BPM");
    require(bpm >= 40 && bpm <= 240, "BPM must be 40..240");
    const auto tail = number(field(plan, "tail_seconds"), "tail seconds");
    require(tail >= 0 && tail <= 1200, "Additional render duration must be 0..1200 seconds");
    auto settings = field(plan, "parameters");
    auto events = field(plan, "events");
    require(settings.isArray() && events.isArray(), "Parameters/events must be arrays");
    juce::AudioFormatManager formats;
    formats.registerBasicFormats();
    require(input.hasFileExtension("wav"), "Use an uncompressed WAV probe for reference capture");
    std::unique_ptr<juce::AudioFormatReader> reader(formats.createReaderFor(input));
    require(reader != nullptr && reader->numChannels == 2 && reader->lengthInSamples > 0
        && reader->lengthInSamples <= reader->sampleRate * 180, "Input must be a stereo audio file of at most 180 seconds");
    const auto rate = reader->sampleRate;
    require(number(field(plan, "sample_rate"), "sample rate") == rate, "Plan/input rates differ; no implicit resampling");
    const int64_t total = reader->lengthInSamples + static_cast<int64_t>(std::llround(rate * tail));
    for (const auto& setting : *settings.getArray()) (void)selectParameter(plugin, setting);
    int64_t last = -1;
    for (const auto& event : *events.getArray()) {
        const auto frame = integer(field(event, "frame"), "event frame");
        require(frame >= 0 && frame >= last && frame < total, "Events must be ordered and lie inside capture");
        last = frame;
        const auto type = field(event, "type").toString();
        if (type == "parameter") (void)selectParameter(plugin, event);
        else if (type == "midi") {
            require(plugin.acceptsMidi(), "Plugin does not accept MIDI events");
            const auto bytes = field(event, "bytes");
            require(bytes.isArray() && bytes.size() >= 1 && bytes.size() <= 3, "MIDI event requires 1..3 bytes");
            for (int i = 0; i < bytes.size(); ++i) {
                const auto byte = integer(bytes[i], "MIDI byte");
                require(byte >= (i == 0 ? 128 : 0) && byte <= (i == 0 ? 255 : 127), "Invalid MIDI status/data byte");
            }
            const auto status = static_cast<int>(bytes[0]);
            const int length = status < 0xf0 ? ((status & 0xe0) == 0xc0 ? 2 : 3)
                : status == 0xf1 || status == 0xf3 ? 2 : status == 0xf2 ? 3
                : status == 0xf6 || status == 0xf8 || status == 0xfa || status == 0xfb
                    || status == 0xfc || status == 0xfe || status == 0xff ? 1 : 0;
            require(length != 0 && bytes.size() == length, "MIDI byte count/status is invalid or unsupported");
        } else throw std::runtime_error("Unknown event type");
    }
    // Reserve a new directory atomically; a crash leaves an incomplete capture,
    // and an existing session can never be silently replaced.
    std::filesystem::create_directories(destination.getParentDirectory().getFullPathName().toStdString());
    require(std::filesystem::create_directory(destination.getFullPathName().toStdString()), "Capture directory already exists");
    auto buses = plugin.getBusesLayout();
    require(buses.inputBuses.size() == 1 && buses.outputBuses.size() == 1, "Expected one input and output bus");
    buses.inputBuses.getReference(0) = juce::AudioChannelSet::stereo();
    buses.outputBuses.getReference(0) = juce::AudioChannelSet::stereo();
    require(plugin.setBusesLayout(buses), "Plugin rejected stereo layout");
    plugin.setNonRealtime(true);
    rmx::host::Playhead head;
    plugin.setPlayHead(&head);
    struct ProcessingScope {
        juce::AudioPluginInstance& instance;
        bool prepared{};
        ~ProcessingScope() {
            if (prepared) instance.releaseResources();
            instance.setPlayHead(nullptr);
        }
    } processing{plugin};
    plugin.prepareToPlay(rate, block);
    processing.prepared = true;
    plugin.reset();
    if (plan.hasProperty("initial_state")) {
        const auto stateDescription = plan["initial_state"];
        const auto stateFile = planFile.getSiblingFile(field(stateDescription, "path").toString());
        require(stateFile.existsAsFile() && stateFile.getSize() <= 16 * 1024 * 1024,
            "Missing/oversized initial plugin state");
        require(juce::SHA256(stateFile).toHexString() == field(stateDescription, "sha256").toString(),
            "Initial plugin state hash mismatch");
        juce::MemoryBlock saved;
        require(stateFile.loadFileAsData(saved), "Cannot read initial plugin state");
        plugin.setStateInformation(saved.getData(), static_cast<int>(saved.getSize()));
    }
    juce::Array<var> parameterLog;
    auto applySetting = [&](const var& setting, int64_t frame) {
        const auto actual = setParameter(plugin, setting);
        parameterLog.add(object({{"frame", static_cast<juce::int64>(frame)},
            {"index", setting["index"]}, {"id", setting["id"]}, {"name", setting["name"]},
            {"requested_value", setting["value"]}, {"immediate_readback", actual}}));
    };
    for (const auto& setting : *settings.getArray()) applySetting(setting, -1);
    auto before = inventory(plugin, description, bundle, registeredIdentifier);
    juce::MemoryBlock state;
    plugin.getStateInformation(state);
    require(destination.getChildFile("state-before.bin").replaceWithData(state.getData(), state.getSize()), "Cannot save plugin state");
    saveJSON(destination.getChildFile("inventory.json"), before);
    require(planFile.copyFileTo(destination.getChildFile("plan.json")), "Cannot preserve capture plan");
    const auto output = destination.getChildFile("audio.wav");
    auto stream = output.createOutputStream();
    require(stream != nullptr && stream->openedOk(), "Cannot create capture audio");
    juce::WavAudioFormat wav;
    std::unique_ptr<juce::AudioFormatWriter> writer(wav.createWriterFor(stream.get(), rate, 2, 32, {}, 0));
    require(writer != nullptr, "Cannot create float WAV writer");
    stream.release();
    juce::AudioBuffer<float> buffer(2, block);
    juce::MidiBuffer midi;
    int eventIndex = 0;
    double maximum = 0;
    for (int64_t position = 0; position < total;) {
        midi.clear();
        while (eventIndex < events.size() && static_cast<int64_t>(events[eventIndex]["frame"]) == position) {
            const auto& event = events[eventIndex++];
            if (event["type"].toString() == "parameter") applySetting(event, position);
            else {
                const auto& values = event["bytes"];
                std::array<juce::uint8, 3> bytes{};
                for (int i = 0; i < values.size(); ++i) bytes[static_cast<size_t>(i)] = static_cast<juce::uint8>(static_cast<int>(values[i]));
                midi.addEvent(bytes.data(), values.size(), 0);
            }
        }
        auto count = static_cast<int>(std::min<int64_t>(block, total - position));
        if (eventIndex < events.size()) count = static_cast<int>(std::min<int64_t>(count, static_cast<int64_t>(events[eventIndex]["frame"]) - position));
        buffer.setSize(2, count, false, false, true);
        buffer.clear();
        const auto available = static_cast<int>(std::max<int64_t>(0, std::min<int64_t>(count, reader->lengthInSamples - position)));
        if (available > 0) require(reader->read(&buffer, 0, available, position, true, true), "Input read failed");
        for (int channel = 0; channel < 2; ++channel) for (int i = 0; i < available; ++i)
            require(std::isfinite(buffer.getSample(channel, i)), "Input contains non-finite audio");
        head.locate(static_cast<double>(position) / rate, rate, bpm, true);
        plugin.processBlock(buffer, midi);
        for (int channel = 0; channel < 2; ++channel) for (int i = 0; i < count; ++i) {
            const auto sample = buffer.getSample(channel, i);
            require(std::isfinite(sample), "Plugin produced non-finite audio");
            maximum = std::max(maximum, std::abs(static_cast<double>(sample)));
        }
        require(writer->writeFromAudioSampleBuffer(buffer, 0, count), "Capture audio write failed");
        position += count;
    }
    writer.reset();
    require(juce::SHA256(planFile).toHexString() == planHash
        && juce::SHA256(destination.getChildFile("plan.json")).toHexString() == planHash,
        "Capture plan changed during rendering");
    require(juce::SHA256(input).toHexString() == inputHash, "Input changed during rendering");
    for (const auto& member : *before["binary_files"].getArray()) {
        const auto file = bundle.isDirectory() ? bundle.getChildFile(member["path"].toString()) : bundle;
        require(juce::SHA256(file).toHexString() == member["sha256"].toString(),
            "Plugin bundle changed during rendering");
    }
    plugin.getStateInformation(state);
    require(destination.getChildFile("state-after.bin").replaceWithData(state.getData(), state.getSize()), "Cannot save final state");
    saveJSON(destination.getChildFile("parameter-log.json"), object({{"kind", "parameter-request-readback-log"},
        {"initial_frame", -1}, {"entries", parameterLog},
        {"scope", "Immediate readback after each request; plugin control-rate response can occur later."}}));
    saveJSON(destination.getChildFile("inventory-after.json"), inventory(plugin, description, bundle, registeredIdentifier));
    saveJSON(destination.getChildFile("receipt.json"), object({{"kind", "audio-plugin-capture"},
        {"schema_version", 1}, {"origin", "software"}, {"role", role}, {"complete", true},
        {"created_at_utc", juce::Time::getCurrentTime().toISO8601(true)}, {"plugin", before},
        {"host_sha256", juce::SHA256(juce::File::getSpecialLocation(juce::File::currentExecutableFile)).toHexString()},
        {"input_path", input.getFullPathName()}, {"input_sha256", inputHash},
        {"plan_sha256", planHash}, {"output_sha256", juce::SHA256(output).toHexString()},
        {"initial_state_sha256", juce::SHA256(destination.getChildFile("state-before.bin")).toHexString()},
        {"final_state_sha256", juce::SHA256(destination.getChildFile("state-after.bin")).toHexString()},
        {"parameter_log_sha256", juce::SHA256(destination.getChildFile("parameter-log.json")).toHexString()},
        {"final_inventory_sha256", juce::SHA256(destination.getChildFile("inventory-after.json")).toHexString()},
        {"sample_rate", rate}, {"frames", static_cast<juce::int64>(total)}, {"maximum_block_size", block},
        {"bpm", bpm}, {"transport_playing", true}, {"offline", true}, {"tail_seconds", tail},
        {"reported_latency_frames", plugin.getLatencySamples()}, {"reported_tail_seconds", plugin.getTailLengthSeconds()},
        {"peak", maximum}}));
    std::cout << destination.getChildFile("receipt.json").getFullPathName() << '\n';
}
}

int main(int argc, char** argv) {
    try {
        String registeredIdentifier;
        std::vector<char*> positional{argv[0]};
        for (int i = 1; i < argc; ++i) {
            if (String(argv[i]) == "--registered-au") {
                require(registeredIdentifier.isEmpty() && i + 1 < argc, "Supply one registered AU identifier");
                registeredIdentifier = argv[++i];
                require(registeredIdentifier.startsWith("AudioUnit:"), "Invalid registered AU identifier");
            } else positional.push_back(argv[i]);
        }
        argc = static_cast<int>(positional.size());
        argv = positional.data();
        require(argc >= 3, "Usage: rmx_reference_host inventory BUNDLE | render BUNDLE INPUT PLAN NEW_DIRECTORY [BLOCK=128] [TIMEOUT=120]");
        const String command(argv[1]);
        require((command == "inventory" && argc == 3) || (command == "render" && argc >= 6 && argc <= 8), "Invalid command or argument count");
        const auto block = argc >= 7 ? std::stoi(argv[6]) : 128;
        const auto timeout = argc == 8 ? std::stoi(argv[7]) : 120;
        require(block >= 8 && block <= 4096 && timeout >= 5 && timeout <= 600, "Invalid block size/watchdog timeout");
        Deadline deadline(timeout);
        juce::ScopedJuceInitialiser_GUI initialise;
        const auto bundle = juce::File::getCurrentWorkingDirectory().getChildFile(argv[2]);
        require(bundle.exists(), "Explicit plugin bundle is missing");
        std::unique_ptr<rmx::host::LocalAudioUnit> localAU;
        if (registeredIdentifier.isEmpty()) localAU = std::make_unique<rmx::host::LocalAudioUnit>(bundle);
        else require(bundle.hasFileExtension("component"), "Registered AU requires an explicit .component bundle");
        const auto lookup = registeredIdentifier.isEmpty() ? bundle.getFullPathName() : registeredIdentifier;
        juce::AudioPluginFormatManager formats;
        formats.addDefaultFormats();
        double rate = 48000;
        if (command == "render") rate = number(field(readJSON(juce::File::getCurrentWorkingDirectory().getChildFile(argv[4])), "sample_rate"), "sample rate");
        require(rate >= 8000 && rate <= 192000, "Sample rate outside 8..192 kHz");
        std::unique_ptr<juce::AudioPluginInstance> plugin;
        juce::PluginDescription description;
       #if JUCE_MAC
        if (bundle.hasFileExtension("vst")) {
            require(registeredIdentifier.isEmpty(), "Legacy VST2 bundles do not use AU registration");
            plugin = std::make_unique<rmx::host::LegacyVST2>(bundle, rate, block);
            description = plugin->getPluginDescription();
        } else
       #endif
        {
            juce::OwnedArray<juce::PluginDescription> descriptions;
            for (auto* format : formats.getFormats()) if (format->fileMightContainThisPluginType(lookup))
                format->findAllTypesForFile(descriptions, lookup);
            require(descriptions.size() == 1, "Expected exactly one plugin in explicit bundle; found " + String(descriptions.size()));
            String error;
            plugin = formats.createPluginInstance(*descriptions[0], rate, block, error);
            require(plugin != nullptr, "Cannot create plugin: " + error);
            description = *descriptions[0];
        }
        if (registeredIdentifier.isNotEmpty()) verifyRegisteredBundleLoaded(bundle);
        if (command == "inventory") std::cout << juce::JSON::toString(inventory(*plugin, description, bundle, registeredIdentifier), false) << '\n';
        else render(*plugin, description, bundle,
            juce::File::getCurrentWorkingDirectory().getChildFile(argv[3]),
            juce::File::getCurrentWorkingDirectory().getChildFile(argv[4]),
            juce::File::getCurrentWorkingDirectory().getChildFile(argv[5]), block, registeredIdentifier);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
