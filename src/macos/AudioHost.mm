#include "AudioHost.h"
#include "rmx/State.h"
#import <Foundation/Foundation.h>
#import <AppKit/NSRunningApplication.h>
#import <CoreAudio/CATapDescription.h>
#import <CoreAudio/AudioHardwareTapping.h>
#include <mach/mach_time.h>
#include <cstring>

namespace {
double hostSeconds(uint64_t ticks) { static const double scale=[] { mach_timebase_info_data_t info; mach_timebase_info(&info); return double(info.numer)/info.denom*1e-9; }(); return ticks*scale; }
uint32_t channelCount(AudioDeviceID id,AudioObjectPropertyScope scope) {
    AudioObjectPropertyAddress a{kAudioDevicePropertyStreamConfiguration,scope,kAudioObjectPropertyElementMain}; UInt32 size=0;
    if(AudioObjectGetPropertyDataSize(id,&a,0,nullptr,&size)!=noErr) return 0;
    std::vector<uint8_t> storage(size); auto* list=reinterpret_cast<AudioBufferList*>(storage.data());
    if(AudioObjectGetPropertyData(id,&a,0,nullptr,&size,list)!=noErr) return 0;
    uint32_t channels=0; for(UInt32 i=0;i<list->mNumberBuffers;++i) channels+=list->mBuffers[i].mNumberChannels; return channels;
}
uint32_t outputStreamLatency(AudioDeviceID device,uint32_t pair) {
    AudioObjectPropertyAddress address{kAudioDevicePropertyStreams,kAudioObjectPropertyScopeOutput,kAudioObjectPropertyElementMain};
    UInt32 bytes=0;
    if(AudioObjectGetPropertyDataSize(device,&address,0,nullptr,&bytes)!=noErr) return 0;
    std::vector<AudioStreamID> streams(bytes/sizeof(AudioStreamID));
    if(AudioObjectGetPropertyData(device,&address,0,nullptr,&bytes,streams.data())!=noErr) return 0;
    uint32_t firstChannel=0,result=0;
    for(auto stream:streams) {
        AudioStreamBasicDescription format{};UInt32 size=sizeof(format);
        AudioObjectPropertyAddress property{kAudioStreamPropertyVirtualFormat,kAudioObjectPropertyScopeGlobal,kAudioObjectPropertyElementMain};
        if(AudioObjectGetPropertyData(stream,&property,0,nullptr,&size,&format)!=noErr) continue;
        if(firstChannel<pair+2&&firstChannel+format.mChannelsPerFrame>pair) {
            UInt32 frames=0;size=sizeof(frames);property.mSelector=kAudioStreamPropertyLatency;
            if(AudioObjectGetPropertyData(stream,&property,0,nullptr,&size,&frames)==noErr) result=std::max(result,frames);
        }
        firstChannel+=format.mChannelsPerFrame;
    }
    return result;
}
double deviceRate(AudioDeviceID id) { AudioObjectPropertyAddress a{kAudioDevicePropertyNominalSampleRate,kAudioObjectPropertyScopeGlobal,kAudioObjectPropertyElementMain}; double v=48000; UInt32 size=sizeof(v); AudioObjectGetPropertyData(id,&a,0,nullptr,&size,&v); return v; }
bool floatFormat(AudioDeviceID id,AudioObjectPropertyScope scope) {
    AudioObjectPropertyAddress a{kAudioDevicePropertyStreamFormat,scope,kAudioObjectPropertyElementMain}; AudioStreamBasicDescription f{}; UInt32 size=sizeof(f);
    return AudioObjectGetPropertyData(id,&a,0,nullptr,&size,&f)==noErr&&f.mFormatID==kAudioFormatLinearPCM&&(f.mFormatFlags&kAudioFormatFlagIsFloat)&&f.mBitsPerChannel==32;
}
uint32_t framesIn(const AudioBufferList* list) {
    if(!list||!list->mNumberBuffers||!list->mBuffers[0].mNumberChannels) return 0;
    return list->mBuffers[0].mDataByteSize/(sizeof(float)*list->mBuffers[0].mNumberChannels);
}
float readChannel(const AudioBufferList* list,uint32_t channel,uint32_t frame) {
    if(!list) return 0;
    for(UInt32 i=0;i<list->mNumberBuffers;++i) {
        const auto& b=list->mBuffers[i];
        if(channel<b.mNumberChannels) return b.mData?static_cast<const float*>(b.mData)[frame*b.mNumberChannels+channel]:0;
        channel-=b.mNumberChannels;
    }
    return 0;
}
void writeChannel(AudioBufferList* list,uint32_t channel,uint32_t frame,float value) {
    for(UInt32 i=0;i<list->mNumberBuffers;++i) { auto& b=list->mBuffers[i]; if(channel<b.mNumberChannels) { if(b.mData) static_cast<float*>(b.mData)[frame*b.mNumberChannels+channel]=value; return; } channel-=b.mNumberChannels; }
}
std::string osError(const char* action,OSStatus code) { return std::string(action)+" (Core Audio error "+std::to_string(code)+")"; }
}
AudioHost::AudioHost(rmx::Engine& e):engine(e) {
    rmx::State state; for(size_t i=0;i<128;++i) cc[i].store(state.cc[i]);
    lastCC.fill(-1);
    MIDIClientCreate(CFSTR("RMX"),nullptr,nullptr,&midiClient);
    MIDIInputPortCreate(midiClient,CFSTR("RMX Controls"),midiCallback,this,&midiInput);
    MIDIOutputPortCreate(midiClient,CFSTR("RMX Feedback"),&midiOutput);
}
AudioHost::~AudioHost() { stop(); if(midiInput) MIDIPortDispose(midiInput); if(midiOutput) MIDIPortDispose(midiOutput); if(midiClient) MIDIClientDispose(midiClient); }
std::vector<MidiSource> AudioHost::midiSources() {
    std::vector<MidiSource> sources;
    for(ItemCount i=0;i<MIDIGetNumberOfSources();++i) { auto source=MIDIGetSource(i); CFStringRef name=nullptr; MIDIObjectGetStringProperty(source,kMIDIPropertyDisplayName,&name); char text[512]{}; if(name) { CFStringGetCString(name,text,sizeof(text),kCFStringEncodingUTF8); CFRelease(name); } sources.push_back({source,text}); }
    return sources;
}
void AudioHost::selectMidiSource(MIDIEndpointRef selected) {
    midiGeneration.fetch_add(1);resetMidiParser.store(true);
    for(ItemCount i=0;i<MIDIGetNumberOfSources();++i) MIDIPortDisconnectSource(midiInput,MIDIGetSource(i));
    if(selected) MIDIPortConnectSource(midiInput,selected,nullptr);
}
std::vector<AudioDevice> AudioHost::devices() {
    AudioObjectPropertyAddress a{kAudioHardwarePropertyDevices,kAudioObjectPropertyScopeGlobal,kAudioObjectPropertyElementMain}; UInt32 size=0;
    AudioObjectGetPropertyDataSize(kAudioObjectSystemObject,&a,0,nullptr,&size);
    std::vector<AudioDeviceID> ids(size/sizeof(AudioDeviceID)); AudioObjectGetPropertyData(kAudioObjectSystemObject,&a,0,nullptr,&size,ids.data());
    std::vector<AudioDevice> result;
    for(auto id:ids) {
        CFStringRef name=nullptr; UInt32 n=sizeof(name); AudioObjectPropertyAddress na{kAudioObjectPropertyName,kAudioObjectPropertyScopeGlobal,kAudioObjectPropertyElementMain};
        AudioObjectGetPropertyData(id,&na,0,nullptr,&n,&name); char text[512]{}; if(name) { CFStringGetCString(name,text,sizeof(text),kCFStringEncodingUTF8); CFRelease(name); }
        result.push_back({id,text,channelCount(id,kAudioObjectPropertyScopeInput),channelCount(id,kAudioObjectPropertyScopeOutput),deviceRate(id)});
    }
    return result;
}
AudioDeviceID AudioHost::defaultOutput() {
    AudioDeviceID id=0; UInt32 size=sizeof(id); AudioObjectPropertyAddress a{kAudioHardwarePropertyDefaultOutputDevice,kAudioObjectPropertyScopeGlobal,kAudioObjectPropertyElementMain}; AudioObjectGetPropertyData(kAudioObjectSystemObject,&a,0,nullptr,&size,&id); return id;
}
bool AudioHost::startRekordbox(AudioDeviceID output,uint32_t outPair,uint32_t bufferFrames,std::string& error) {
    stop();
    if(@available(macOS 14.2,*)) {
        NSArray<NSRunningApplication*>* apps=[NSRunningApplication runningApplicationsWithBundleIdentifier:@"com.pioneerdj.rekordboxdj"];
        if(apps.count==0) { error="Open rekordbox before starting direct capture."; return false; }
        pid_t pid=apps.firstObject.processIdentifier; AudioObjectID object=0; UInt32 size=sizeof(object);
        AudioObjectPropertyAddress processAddress{kAudioHardwarePropertyTranslatePIDToProcessObject,kAudioObjectPropertyScopeGlobal,kAudioObjectPropertyElementMain};
        AudioObjectGetPropertyData(kAudioObjectSystemObject,&processAddress,sizeof(pid),&pid,&size,&object);
        CATapDescription* description=[[CATapDescription alloc] initStereoMixdownOfProcesses:object?@[@(object)]:@[]];
        bool usesBundleIdentity=false;
#if __MAC_OS_X_VERSION_MAX_ALLOWED >= 260000
        if(@available(macOS 26.0,*)) { description.bundleIDs=@[@"com.pioneerdj.rekordboxdj"]; description.processRestoreEnabled=YES; usesBundleIdentity=true; }
#endif
        if(!usesBundleIdentity&&!object) { error="Play a track in rekordbox once, then start direct capture."; return false; }
        description.name=@"RMX rekordbox input"; description.privateTap=YES; description.muteBehavior=CATapMutedWhenTapped;
        startupStage.store("Requesting rekordbox audio access");
        AudioObjectID tap=0; OSStatus status=AudioHardwareCreateProcessTap(description,&tap);
        if(status) { error=osError("Cannot capture rekordbox; allow RMX audio capture in System Settings",status); return false; }
        CFStringRef outputUID=nullptr; size=sizeof(outputUID); AudioObjectPropertyAddress uid{kAudioDevicePropertyDeviceUID,kAudioObjectPropertyScopeGlobal,kAudioObjectPropertyElementMain};
        status=AudioObjectGetPropertyData(output,&uid,0,nullptr,&size,&outputUID);
        if(status||!outputUID) { AudioHardwareDestroyProcessTap(tap); error="Cannot identify the selected output device."; return false; }
        NSString* outputName=CFBridgingRelease(outputUID);
        NSDictionary* composition=@{
            @kAudioAggregateDeviceNameKey:@"RMX Direct Capture",
            @kAudioAggregateDeviceUIDKey:NSUUID.UUID.UUIDString,
            @kAudioAggregateDeviceIsPrivateKey:@YES,
            @kAudioAggregateDeviceIsStackedKey:@NO,
            @kAudioAggregateDeviceMainSubDeviceKey:outputName,
            @kAudioAggregateDeviceSubDeviceListKey:@[@{@kAudioSubDeviceUIDKey:outputName}],
            @kAudioAggregateDeviceTapListKey:@[@{@kAudioSubTapUIDKey:description.UUID.UUIDString,@kAudioSubTapDriftCompensationKey:@YES}]
        };
        startupStage.store("Connecting rekordbox to the selected output");
        AudioDeviceID aggregate=0; status=AudioHardwareCreateAggregateDevice((__bridge CFDictionaryRef)composition,&aggregate);
        if(status) { AudioHardwareDestroyProcessTap(tap); error=osError("Cannot create direct audio route",status); return false; }
        // Physical input channels precede the tap channels in a mixed aggregate.
        const uint32_t physicalInputs=channelCount(output,kAudioObjectPropertyScopeInput);
        if(!start(aggregate,aggregate,physicalInputs,outPair,bufferFrames,error)) { AudioHardwareDestroyAggregateDevice(aggregate); AudioHardwareDestroyProcessTap(tap); return false; }
        processTap=tap; tapAggregate=aggregate; return true;
    }
    error="Direct application capture needs macOS 14.2 or later. Use BlackHole or a physical interface."; return false;
}
bool AudioHost::start(AudioDeviceID input,AudioDeviceID output,uint32_t inPair,uint32_t outPair,uint32_t bufferFrames,std::string& error) {
    stop(); error.clear(); inputID=input; outputID=output; inputPair=inPair; outputPair=outPair;
    startupStage.store("Configuring the audio device");
    if(!output||channelCount(output,kAudioObjectPropertyScopeOutput)<outPair+2) { error="Select a stereo output pair."; return false; }
    if(input&&channelCount(input,kAudioObjectPropertyScopeInput)<inPair+2) { error="Select a stereo line input pair (not a microphone)."; return false; }
    if(!floatFormat(output,kAudioObjectPropertyScopeOutput)||(input&&!floatFormat(input,kAudioObjectPropertyScopeInput))) { error="Device must expose 32-bit float Core Audio streams."; return false; }
    AudioObjectPropertyAddress bs{kAudioDevicePropertyBufferFrameSize,kAudioObjectPropertyScopeGlobal,kAudioObjectPropertyElementMain};
    AudioObjectSetPropertyData(output,&bs,0,nullptr,sizeof(bufferFrames),&bufferFrames);
    if(input&&input!=output) AudioObjectSetPropertyData(input,&bs,0,nullptr,sizeof(bufferFrames),&bufferFrames);
    outputRate=deviceRate(output); inputRate=input?deviceRate(input):outputRate;
    startupStage.store("Preparing audio processing");
    engine.prepare(outputRate,maxFrames); midiGeneration.fetch_add(1);resetMidiParser.store(true);writeIndex.store(0); readIndex.store(0); fraction=0; primed=false; targetFill=std::min(bufferFrames*3,4096u);
    underruns.store(0); overruns.store(0); pickedUp.fill(false); lastCC.fill(-1);
    UInt32 actual=sizeof(bufferFrames); AudioObjectGetPropertyData(output,&bs,0,nullptr,&actual,&bufferFrames);
    auto latency=[&](AudioDeviceID id,AudioObjectPropertyScope scope) { UInt32 v=0,s=sizeof(v); AudioObjectPropertyAddress a{kAudioDevicePropertyLatency,scope,kAudioObjectPropertyElementMain}; AudioObjectGetPropertyData(id,&a,0,nullptr,&s,&v); return v; };
    // IOProc output mHostTime already expresses scheduled buffer output time.
    // Device and stream latency still lie between that timestamp and the DAC.
    outputLatencySeconds=(latency(output,kAudioObjectPropertyScopeOutput)+outputStreamLatency(output,outPair))/outputRate;
    ioLatencyMs=static_cast<float>((bufferFrames*2+latency(output,kAudioObjectPropertyScopeOutput)+(input?latency(input,kAudioObjectPropertyScopeInput):0)+(input&&input!=output?targetFill:0))*1000/outputRate);
    latencyMs.store(ioLatencyMs+static_cast<float>(engine.latencySamples()*1000/outputRate));
    startupStage.store("Opening the audio output");
    OSStatus status=AudioDeviceCreateIOProcID(output,callback,this,&outputProc);
    if(status) { error=osError("Cannot create output callback",status); stop(); return false; }
    if(input&&input!=output) {
        status=AudioDeviceCreateIOProcID(input,callback,this,&inputProc);
        if(status) { error=osError("Cannot create input callback",status); stop(); return false; }
        status=AudioDeviceStart(input,inputProc);
        if(status) { error=osError("Cannot start input; check microphone permission",status); stop(); return false; }
    }
    active.store(true);
    startupStage.store("Starting audio playback");
    status=AudioDeviceStart(output,outputProc);
    if(status) { error=osError("Cannot start output",status); stop(); return false; }
    for(auto selector:{kAudioDevicePropertyDeviceIsAlive,kAudioDevicePropertyNominalSampleRate}) {
        AudioObjectPropertyAddress a{selector,kAudioObjectPropertyScopeGlobal,kAudioObjectPropertyElementMain};
        AudioObjectAddPropertyListener(outputID,&a,propertyCallback,this);
        if(inputID&&inputID!=outputID) AudioObjectAddPropertyListener(inputID,&a,propertyCallback,this);
    }
    deviceChanged.store(false); startupStage.store("Audio running"); return true;
}
void AudioHost::stop() {
    active.store(false);
    startupStage.store("Stopping audio");
    for(auto selector:{kAudioDevicePropertyDeviceIsAlive,kAudioDevicePropertyNominalSampleRate}) {
        AudioObjectPropertyAddress a{selector,kAudioObjectPropertyScopeGlobal,kAudioObjectPropertyElementMain};
        if(outputID) AudioObjectRemovePropertyListener(outputID,&a,propertyCallback,this);
        if(inputID&&inputID!=outputID) AudioObjectRemovePropertyListener(inputID,&a,propertyCallback,this);
    }
    if(inputProc) { AudioDeviceStop(inputID,inputProc); AudioDeviceDestroyIOProcID(inputID,inputProc); inputProc=nullptr; }
    if(outputProc) { AudioDeviceStop(outputID,outputProc); AudioDeviceDestroyIOProcID(outputID,outputProc); outputProc=nullptr; }
    if(@available(macOS 14.2,*)) { if(tapAggregate) { AudioHardwareDestroyAggregateDevice(tapAggregate); tapAggregate=0; } if(processTap) { AudioHardwareDestroyProcessTap(processTap); processTap=0; } }
}
OSStatus AudioHost::propertyCallback(AudioObjectID,UInt32,const AudioObjectPropertyAddress[],void* user) {
    static_cast<AudioHost*>(user)->deviceChanged.store(true); return noErr;
}
OSStatus AudioHost::callback(AudioDeviceID device,const AudioTimeStamp*,const AudioBufferList* input,const AudioTimeStamp*,AudioBufferList* output,const AudioTimeStamp* outputTime,void* user) {
    auto& h=*static_cast<AudioHost*>(user);
    if(device==h.inputID&&device!=h.outputID) h.capture(input);
    if(device==h.outputID) h.render(h.inputID==h.outputID?input:nullptr,output,outputTime);
    return noErr;
}
void AudioHost::capture(const AudioBufferList* input) noexcept {
    auto w=writeIndex.load(std::memory_order_relaxed); const auto r=readIndex.load(std::memory_order_acquire);
    const uint32_t count=framesIn(input);
    if(w-r+count>=ringSize) { overruns.fetch_add(1,std::memory_order_relaxed); return; }
    for(uint32_t i=0;i<count;++i) ring[(w+i)&(ringSize-1)]={readChannel(input,inputPair,i),readChannel(input,inputPair+1,i)};
    writeIndex.store(w+count,std::memory_order_release);
}
void AudioHost::render(const AudioBufferList* input,AudioBufferList* output,const AudioTimeStamp* outputTime) noexcept {
    if(!output) return;
    const auto start=mach_absolute_time(); const uint32_t count=framesIn(output);
    for(UInt32 b=0;b<output->mNumberBuffers;++b) if(output->mBuffers[b].mData) std::memset(output->mBuffers[b].mData,0,output->mBuffers[b].mDataByteSize);
    if(!active.load()||count>maxFrames) { if(count>maxFrames) overruns.fetch_add(1); return; }
    auto r=readIndex.load(std::memory_order_relaxed); const auto w=writeIndex.load(std::memory_order_acquire);
    if(inputID!=outputID&&inputID&&!primed&&w-r>=targetFill) primed=true;
    const double drift=std::clamp((static_cast<double>(w-r)-targetFill)/std::max(1.,static_cast<double>(targetFill))*.0002,-.002,.002);
    const double step=inputRate/outputRate*(1+drift);
    bool starved=false;
    for(uint32_t i=0;i<count;++i) {
        rmx::Stereo x{};
        if(inputID==outputID) x={readChannel(input,inputPair,i),readChannel(input,inputPair+1,i)};
        else if(inputID&&primed&&r+1<w) {
            x=rmx::mix(ring[r&(ringSize-1)],ring[(r+1)&(ringSize-1)],static_cast<float>(fraction)); fraction+=step;
            const auto advance=static_cast<uint64_t>(fraction); fraction-=advance;
            if(advance>w-r) { r=w; fraction=0; starved=true; } else r+=advance;
        } else if(inputID&&primed) starved=true;
        left[i]=x.l; right[i]=x.r;
    }
    if(starved) { underruns.fetch_add(1,std::memory_order_relaxed); primed=false; fraction=0; }
    readIndex.store(r,std::memory_order_release);
    std::array<rmx::Event,256> events{}; size_t eventCount=0; processMidi(events,eventCount);
    rmx::Transport t;
    const uint64_t outputHost=outputTime&&(outputTime->mFlags&kAudioTimeStampHostTimeValid)?outputTime->mHostTime:start;
    const double processingSeconds=engine.latencySamples()/outputRate;
    latencyMs.store(ioLatencyMs+static_cast<float>(processingSeconds*1000),std::memory_order_relaxed);
    const auto audibleMicros=static_cast<int64_t>((hostSeconds(outputHost)+outputLatencySeconds+processingSeconds)*1.e6);
    const bool linked=link.capture(audibleMicros,t);
    if(!linked) { const auto clock=midiClock.position(hostSeconds(outputHost)+outputLatencySeconds+processingSeconds);if(clock.synced) { t.synced=true;t.bpm=clock.bpm;t.beat=clock.beat;t.playing=clock.playing; } }
    engine.process(left.data(),right.data(),outLeft.data(),outRight.data(),count,t,std::span<const rmx::Event>(events.data(),eventCount));
    for(uint32_t i=0;i<count;++i) { writeChannel(output,outputPair,i,outLeft[i]); writeChannel(output,outputPair+1,i,outRight[i]); }
    const float load=static_cast<float>(hostSeconds(mach_absolute_time()-start)/(count/outputRate)); callbackLoad.store(load,std::memory_order_relaxed); engine.meters.load.store(load,std::memory_order_relaxed);
}
void AudioHost::midiCallback(const MIDIPacketList* list,void* user,void*) {
    auto& h=*static_cast<AudioHost*>(user); if(!h.midiEnabled.load()) return;
    const MIDIPacket* packet=&list->packet[0];
    const auto generation=h.midiGeneration.load();
    if(h.resetMidiParser.exchange(false)) h.midiParser.reset();
    for(UInt32 p=0;p<list->numPackets;++p) {
        for(UInt16 i=0;i<packet->length;++i) {
            const uint64_t time=packet->timeStamp?packet->timeStamp:mach_absolute_time();
            h.midiParser.byte(packet->data[i],[&](uint8_t status,uint8_t a,uint8_t b) {
                if(!h.midi.push({status,a,b,time,generation})) h.midiDrops.fetch_add(1,std::memory_order_relaxed);
            });
        }
        packet=MIDIPacketNext(packet);
    }
}

void AudioHost::processMidi(std::array<rmx::Event,256>& events,size_t& count) noexcept {
    const auto generation=midiGeneration.load();
    if(consumedMidiGeneration!=generation) { midiClock.reset();consumedMidiGeneration=generation; }
    Midi m;
    while(midi.pop(m)) {
        if(m.generation!=generation) continue;
        auto add=[&](rmx::EventType type,int pad=0,float velocity=1) { if(count<events.size()) events[count++]={type,static_cast<uint8_t>(pad),velocity,0}; else midiDrops.fetch_add(1,std::memory_order_relaxed); };
        if((m.status&0xf0)==0x90&&m.b&&m.a>=36&&m.a<=39) add(rmx::EventType::Trigger,m.a-36,m.b/127.f);
        if((m.status&0xf0)==0xb0) {
            const int learning=learnTarget.exchange(-1);
            if(learning>=0) { cc[m.a].store(learning); learnedCC.store(m.a); pickedUp[m.a]=false; }
            const int index=cc[m.a].load();
            if(index>=0&&index<static_cast<int>(rmx::parameterCount)) {
                const auto param=static_cast<rmx::Param>(index); const auto& info=rmx::parameters[static_cast<size_t>(index)];
                const float v=m.b/127.f, current=(engine.params.get(param)-info.min)/(info.max-info.min);
                if(std::abs(v-current)<.035f||(lastCC[m.a]>=0&&(lastCC[m.a]-current)*(v-current)<=0)) pickedUp[m.a]=true;
                lastCC[m.a]=v; if(pickedUp[m.a]) engine.params.set(param,info.min+v*(info.max-info.min));
            }
            if(m.a==64) add(m.b>=64?rmx::EventType::RollStart:rmx::EventType::RollStop);
            if(m.a==123) add(rmx::EventType::Panic);
        }
        midiClock.receive(m.status,m.a,m.b,hostSeconds(m.time));
        if(m.status==0xfc) add(rmx::EventType::RollStop);
    }
}
void AudioHost::sendFeedback(rmx::Param p,float normalized) {
    if(!midiOutput||!feedbackEnabled) return;
    for(size_t i=0;i<128;++i) if(cc[i].load()==static_cast<int>(p)) {
        uint8_t bytes[]{0xb0,static_cast<uint8_t>(i),static_cast<uint8_t>(std::clamp(normalized,0.f,1.f)*127)};
        alignas(MIDIPacketList) uint8_t storage[128]{}; auto* list=reinterpret_cast<MIDIPacketList*>(storage); auto* packet=MIDIPacketListInit(list); MIDIPacketListAdd(list,sizeof(storage),packet,0,3,bytes);
        for(ItemCount d=0;d<MIDIGetNumberOfDestinations();++d) MIDISend(midiOutput,MIDIGetDestination(d),list);
    }
}
