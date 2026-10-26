#pragma once
#include "rmx/Engine.h"
#include "LinkSession.h"
#include "rmx/MidiClock.h"
#include <CoreAudio/CoreAudio.h>
#include <CoreMIDI/CoreMIDI.h>
#include <array>
#include <atomic>
#include <string>
#include <vector>

struct AudioDevice {
    AudioDeviceID id{};
    std::string name;
    uint32_t inputs{},outputs{};
    double rate{};
};
struct MidiSource { MIDIEndpointRef id{}; std::string name; };
class AudioHost {
public:
    explicit AudioHost(rmx::Engine& engine);
    ~AudioHost();
    static std::vector<AudioDevice> devices();
    static std::vector<MidiSource> midiSources();
    void selectMidiSource(MIDIEndpointRef);
    bool start(AudioDeviceID input,AudioDeviceID output,uint32_t inPair,uint32_t outPair,uint32_t bufferFrames,std::string& error);
    bool startRekordbox(AudioDeviceID output,uint32_t outPair,uint32_t bufferFrames,std::string& error);
    static AudioDeviceID defaultOutput();
    void stop();
    bool running() const { return active.load(); }
    void setMidiEnabled(bool on) { midiEnabled.store(on); midiGeneration.fetch_add(1); resetMidiParser.store(true); }
    void sendFeedback(rmx::Param,float normalized);
    static bool linkAvailable() noexcept { return LinkSession::available(); }
    void setLinkEnabled(bool on) { link.enable(on); }
    bool linkEnabled() const noexcept { return link.enabled(); }
    unsigned linkPeers() const noexcept { return link.peers(); }
    std::array<std::atomic<int>,128> cc;
    std::atomic<int> learnTarget{-1},learnedCC{-1};
    std::atomic<uint64_t> underruns{},overruns{},midiDrops{};
    std::atomic<float> latencyMs{},callbackLoad{};
    std::atomic<bool> active{};
    std::atomic<bool> deviceChanged{};
    std::atomic<const char*> startupStage{"Audio stopped"};
    bool feedbackEnabled{false};
    double rate() const { return outputRate; }
private:
    rmx::Engine& engine;
    LinkSession link;
    AudioDeviceID inputID{},outputID{};
    AudioObjectID processTap{};
    AudioDeviceID tapAggregate{};
    AudioDeviceIOProcID inputProc{},outputProc{};
    uint32_t inputPair{},outputPair{};
    double inputRate{48000},outputRate{48000},outputLatencySeconds{};float ioLatencyMs{};
    static constexpr uint32_t ringSize=65536,maxFrames=8192;
    std::array<rmx::Stereo,ringSize> ring{};
    std::atomic<uint64_t> writeIndex{},readIndex{};
    double fraction{}; bool primed{}; uint32_t targetFill{256};
    std::array<float,maxFrames> left{},right{},outLeft{},outRight{};
    struct Midi { uint8_t status{},a{},b{}; uint64_t time{}; uint32_t generation{}; };
    rmx::SpscQueue<Midi,1024> midi;
    std::array<float,128> lastCC{}; std::array<bool,128> pickedUp{};
    std::atomic<bool> midiEnabled{true};
    MIDIClientRef midiClient{}; MIDIPortRef midiInput{},midiOutput{};
    rmx::MidiClock midiClock;
    rmx::MidiStreamParser midiParser;
    std::atomic<bool> resetMidiParser{};
    std::atomic<uint32_t> midiGeneration{1};uint32_t consumedMidiGeneration{};
    static OSStatus callback(AudioDeviceID,const AudioTimeStamp*,const AudioBufferList*,const AudioTimeStamp*,AudioBufferList*,const AudioTimeStamp*,void*);
    static OSStatus propertyCallback(AudioObjectID,UInt32,const AudioObjectPropertyAddress[],void*);
    static void midiCallback(const MIDIPacketList*,void*,void*);
    void processMidi(std::array<rmx::Event,256>& events,size_t& count) noexcept;
    void capture(const AudioBufferList*) noexcept;
    void render(const AudioBufferList*,AudioBufferList*,const AudioTimeStamp*) noexcept;
};
