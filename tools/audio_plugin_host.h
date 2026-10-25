#pragma once
#include <juce_audio_utils/juce_audio_utils.h>
#include <array>
#include <cmath>
#include <memory>
#include <stdexcept>
#include <string>
#if JUCE_MAC
 #include <AudioToolbox/AudioToolbox.h>
 #include <CoreFoundation/CoreFoundation.h>
#endif

namespace rmx::host {
// AudioComponentRegister is a public, process-local registration API. This
// loads the factory from the explicitly requested AUv2 bundle; it does not copy
// a component into a system/user plugin folder or update the global registry.
class LocalAudioUnit {
public:
    explicit LocalAudioUnit(const juce::File& file) {
       #if JUCE_MAC
        if (!file.hasFileExtension(".component")) return;
        const auto path = file.getFullPathName().toUTF8();
        auto* url = CFURLCreateFromFileSystemRepresentation(kCFAllocatorDefault,
            reinterpret_cast<const UInt8*>(path.getAddress()), static_cast<CFIndex>(path.sizeInBytes() - 1), true);
        if (url == nullptr) throw std::runtime_error("Cannot form explicit AU bundle URL");
        bundle.reset(CFBundleCreate(kCFAllocatorDefault, url));
        CFRelease(url);
        if (!bundle) throw std::runtime_error("Cannot open explicit AU bundle");
        auto components = CFBundleGetValueForInfoDictionaryKey(bundle.get(), CFSTR("AudioComponents"));
        if (components == nullptr || CFGetTypeID(components) != CFArrayGetTypeID() ||
            CFArrayGetCount(static_cast<CFArrayRef>(components)) != 1)
            throw std::runtime_error("Expected one AudioComponents entry in explicit AU bundle");
        auto entry = static_cast<CFDictionaryRef>(CFArrayGetValueAtIndex(static_cast<CFArrayRef>(components), 0));
        if (entry == nullptr || CFGetTypeID(entry) != CFDictionaryGetTypeID())
            throw std::runtime_error("Invalid AU component dictionary");
        auto stringValue = [entry](CFStringRef key) -> CFStringRef {
            auto value = CFDictionaryGetValue(entry, key);
            if (value == nullptr || CFGetTypeID(value) != CFStringGetTypeID())
                throw std::runtime_error("Missing AU string metadata");
            return static_cast<CFStringRef>(value);
        };
        auto code = [entry](CFStringRef key) -> OSType {
            auto value = CFDictionaryGetValue(entry, key);
            if (value != nullptr && CFGetTypeID(value) == CFNumberGetTypeID()) {
                int64_t number = 0;
                if (CFNumberGetValue(static_cast<CFNumberRef>(value), kCFNumberSInt64Type, &number) && number > 0 && number <= UINT32_MAX)
                    return static_cast<OSType>(number);
            }
            if (value != nullptr && CFGetTypeID(value) == CFStringGetTypeID() &&
                CFStringGetLength(static_cast<CFStringRef>(value)) == 4) {
                std::array<char, 5> bytes{};
                if (CFStringGetCString(static_cast<CFStringRef>(value), bytes.data(), bytes.size(), kCFStringEncodingASCII)) {
                    OSType result = 0;
                    for (size_t i = 0; i < 4; ++i) result = (result << 8) | static_cast<unsigned char>(bytes[i]);
                    return result;
                }
            }
            throw std::runtime_error("Invalid AU four-character component metadata");
        };
        AudioComponentDescription description{};
        description.componentType = code(CFSTR("type"));
        description.componentSubType = code(CFSTR("subtype"));
        description.componentManufacturer = code(CFSTR("manufacturer"));
        int64_t version = 0;
        auto versionValue = CFDictionaryGetValue(entry, CFSTR("version"));
        if (versionValue == nullptr || CFGetTypeID(versionValue) != CFNumberGetTypeID() ||
            !CFNumberGetValue(static_cast<CFNumberRef>(versionValue), kCFNumberSInt64Type, &version) ||
            version < 0 || version > UINT32_MAX)
            throw std::runtime_error("Invalid AU component version");
        const auto factoryName = stringValue(CFSTR("factoryFunction"));
        if (!CFBundleLoadExecutable(bundle.get())) throw std::runtime_error("Cannot load explicit AU bundle executable");
        auto* function = CFBundleGetFunctionPointerForName(bundle.get(), factoryName);
        if (function == nullptr) throw std::runtime_error("AU factoryFunction symbol not found in explicit bundle");
        // The SDK defines sandboxSafe as an opt-in claim from bundle metadata.
        // Do not set it merely to try to bypass a failed registration.
        const auto sandboxSafe = CFDictionaryGetValue(entry, CFSTR("sandboxSafe"));
        if (sandboxSafe != nullptr && CFGetTypeID(sandboxSafe) == CFBooleanGetTypeID() &&
            CFBooleanGetValue(static_cast<CFBooleanRef>(sandboxSafe)))
            description.componentFlags |= kAudioComponentFlag_SandboxSafe;
        AudioComponentDescription anyComponent{};
        visibleComponentsBefore = AudioComponentCount(&anyComponent);
        const auto matchingBefore = AudioComponentCount(&description);
        auto component = AudioComponentRegister(&description, stringValue(CFSTR("name")), static_cast<UInt32>(version),
            reinterpret_cast<AudioComponentFactoryFunction>(function));
        if (component == nullptr) throw std::runtime_error("Process-local AudioComponentRegister returned null; visible_system_components=" +
            std::to_string(visibleComponentsBefore) + "; matching_before=" + std::to_string(matchingBefore) +
            "; matching_after=" + std::to_string(AudioComponentCount(&description)) + "; component_flags=" +
            std::to_string(description.componentFlags) + "; factory_symbol_resolved=true; public API supplies no OSStatus");
        // JUCE resolves AU descriptions via AudioComponentFindNext. Prove it
        // will select our explicit factory rather than another installed build.
        if (AudioComponentFindNext(nullptr, &description) != component)
            throw std::runtime_error("Explicit AU registration is shadowed by another component; refusing an ambiguous test");
        registered = true;
        factory = juce::String::fromCFString(factoryName);
       #else
        (void)file;
       #endif
    }
    bool registered{};
    juce::String factory;
    unsigned visibleComponentsBefore{};
private:
   #if JUCE_MAC
    struct BundleRelease { void operator()(CFBundleRef value) const { CFRelease(value); } };
    // Declared before the format manager and processor, so the executable stays
    // loaded until both have been destroyed. Never explicitly unload its code.
    std::unique_ptr<std::remove_pointer_t<CFBundleRef>, BundleRelease> bundle;
   #endif
};

class Playhead final : public juce::AudioPlayHead {
public:
    PositionInfo position;
    juce::Optional<PositionInfo> getPosition() const override { return position; }
    void locate(double seconds, double rate, double bpm, bool playing) {
        position.setTimeInSeconds(seconds);
        position.setTimeInSamples(static_cast<juce::int64>(std::llround(seconds * rate)));
        position.setBpm(bpm);
        position.setPpqPosition(seconds * bpm / 60);
        position.setPpqPositionOfLastBarStart(std::floor(seconds * bpm / 240) * 4);
        position.setTimeSignature(TimeSignature{4, 4});
        position.setIsPlaying(playing);
        position.setIsRecording(false);
    }
};

} // namespace rmx::host
