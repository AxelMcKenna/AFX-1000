#include <juce_audio_utils/juce_audio_utils.h>
#include "rmx/Engine.h"
#include "rmx/State.h"
#include "rmx/Wav.h"
#include "rmx/MidiClock.h"
#include <memory>

namespace {
juce::String js(std::string_view text) { return juce::String::fromUTF8(text.data(),static_cast<int>(text.size())); }
juce::Colour orange=juce::Colour::fromRGB(255,110,41),cyan=juce::Colour::fromRGB(46,209,222);
}
class RMXEditor;
class RMXProcessor final : public juce::AudioProcessor,private juce::Timer {
public:
    rmx::Engine engine;
    juce::AudioProcessorValueTreeState tree;
    rmx::State state;
    juce::String assetMessage;
    RMXProcessor():AudioProcessor(BusesProperties().withInput("Stereo input",juce::AudioChannelSet::stereo(),true).withOutput("Stereo output",juce::AudioChannelSet::stereo(),true)),tree(*this,nullptr,"RMX",layout()) {
        for(size_t i=0;i<rmx::parameterCount;++i) { raw[i]=tree.getRawParameterValue(js(rmx::parameters[i].id)); pendingValues[i].store(std::numeric_limits<float>::quiet_NaN()); }
        lastCC.fill(-1);
        publish(rmx::makeFactoryBank()); startTimerHz(30);
    }
    ~RMXProcessor() override { stopTimer(); }
    static juce::AudioProcessorValueTreeState::ParameterLayout layout() {
        juce::AudioProcessorValueTreeState::ParameterLayout result;
        for(size_t i=0;i<rmx::parameterCount;++i) {
            const auto& p=rmx::parameters[i];const auto choices=rmx::parameterChoices(static_cast<rmx::Param>(i));
            if(!choices.empty()) {
                juce::StringArray names;for(auto name:choices) names.add(js(name));
                result.add(std::make_unique<juce::AudioParameterChoice>(juce::ParameterID(js(p.id),1),js(p.name),names,static_cast<int>(p.initial)));
            } else result.add(std::make_unique<juce::AudioParameterFloat>(juce::ParameterID(js(p.id),1),js(p.name),juce::NormalisableRange<float>(p.min,p.max,p.discrete?1.f:0.f),p.initial));
        }
        return result;
    }
    const juce::String getName() const override { return "RMX"; }
    bool acceptsMidi() const override { return true; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override {
        const bool user=engine.params.get(rmx::Param::UserSettings)>.5f;
        auto effective=[&](rmx::Param p) {
            const auto& info=rmx::parameters[static_cast<size_t>(p)];
            return !user&&info.advanced?info.initial:engine.params.get(p);
        };
        const int type=static_cast<int>(effective(rmx::Param::SceneType));
        double beats=1;
        for(const auto group:rmx::sceneDelayGroups)if(group.scene==type) {
            const auto position=effective(rmx::Param::SceneTime);
            const auto region=type==1?rmx::echoDelayRegion(position):rmx::sceneDelayRegion(position);
            const auto p=static_cast<rmx::Param>(static_cast<size_t>(group.first)+region);
            beats=rmx::sceneDelayBeats[static_cast<size_t>(effective(p))];
        }
        constexpr std::array feedbackParams{rmx::Param::BpfFeedbackChar,rmx::Param::EchoFeedbackChar,
            rmx::Param::EchoFeedbackChar,rmx::Param::SpiralUpFeedbackChar,rmx::Param::EchoFeedbackChar,
            rmx::Param::HpfFeedbackChar,rmx::Param::LpfFeedbackChar,rmx::Param::CrushFeedbackChar,
            rmx::Param::SpiralDownFeedbackChar,rmx::Param::EchoFeedbackChar};
        constexpr double characters[]{.65,1,1.45};
        const double delay=60/std::max(40.f,effective(rmx::Param::Tempo))*beats;
        const double feedback=std::clamp(effective(rmx::Param::Feedback)*characters[static_cast<size_t>(effective(feedbackParams[type]))],.01,.96);
        // Hold is intentionally unbounded; offline holds require an explicit
        // render duration. Report the finite decaying tail for other states.
        // One-shots can play four times slower at -24 semitones. Sampler loops,
        // like held echoes, need an explicit offline render duration.
        return std::max(120.,delay*std::log(.0001)/std::log(feedback)+2);
    }
    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram(int) override {}
    const juce::String getProgramName(int) override { return "Performance"; }
    void changeProgramName(int,const juce::String&) override {}
    bool hasEditor() const override { return true; }
    juce::AudioProcessorEditor* createEditor() override;
    bool isBusesLayoutSupported(const BusesLayout& b) const override { return b.getMainInputChannelSet()==juce::AudioChannelSet::stereo()&&b.getMainOutputChannelSet()==juce::AudioChannelSet::stereo(); }
    void prepareToPlay(double rate,int block) override {
        for(size_t i=0;i<rmx::parameterCount;++i) engine.params.set(static_cast<rmx::Param>(i),raw[i]->load());
        engine.setBank(&published.load()->bank); engine.prepare(rate,static_cast<uint32_t>(block));
        midiClock.reset();sampleClock=0;hostBeatEstimate=0;midiRollStopPending=false;
    }
    void releaseResources() override {}
    void processBlock(juce::AudioBuffer<float>& buffer,juce::MidiBuffer& midi) override {
        juce::ScopedNoDenormals noDenormals;
        if(buffer.getNumChannels()<2) { buffer.clear(); return; }
        for(size_t i=0;i<rmx::parameterCount;++i) engine.params.set(static_cast<rmx::Param>(i),raw[i]->load(std::memory_order_relaxed));
        const auto* assets=published.load(std::memory_order_acquire); engine.setBank(&assets->bank);
        std::array<rmx::Event,256> events{}; size_t count=0;
        struct ClockEvent { uint32_t offset;uint8_t status,a,b; };
        std::array<ClockEvent,256> clocks{};size_t clockCount=0;
        const auto frames=static_cast<uint32_t>(buffer.getNumSamples());
        if(!frames) { midi.clear();return; }
        for(const auto metadata:midi) {
            const auto* bytes=metadata.data; const int size=metadata.numBytes;
            if(size>=3&&(bytes[0]&0xf0)==0x90&&bytes[2]>0&&bytes[1]>=36&&bytes[1]<=39) {
                if(count<events.size()) events[count++]=engine.captureEvent({rmx::EventType::Trigger,static_cast<uint8_t>(bytes[1]-36),bytes[2]/127.f,static_cast<uint32_t>(std::max(0,metadata.samplePosition))});
                else engine.meters.droppedEvents.fetch_add(1,std::memory_order_relaxed);
            }
            if(size>=3&&(bytes[0]&0xf0)==0xb0) {
                const int index=ccMap[bytes[1]].load(std::memory_order_relaxed);
                if(index>=0&&index<static_cast<int>(rmx::parameterCount)) {
                    const auto& p=rmx::parameters[static_cast<size_t>(index)]; const float normal=bytes[2]/127.f,current=(engine.params.get(static_cast<rmx::Param>(index))-p.min)/(p.max-p.min);
                    if(std::abs(normal-current)<.035f||(lastCC[bytes[1]]>=0&&(lastCC[bytes[1]]-current)*(normal-current)<=0)) pickedUp[bytes[1]]=true;
                    lastCC[bytes[1]]=normal;
                    if(pickedUp[bytes[1]]) { const float v=p.min+(p.max-p.min)*normal; engine.params.set(static_cast<rmx::Param>(index),v); pendingValues[static_cast<size_t>(index)].store(v,std::memory_order_relaxed); }
                }
            }
            if(size>=1&&(bytes[0]==0xf8||bytes[0]==0xfa||bytes[0]==0xfb||bytes[0]==0xfc||(bytes[0]==0xf2&&size>=3))) {
                if(clockCount<clocks.size())clocks[clockCount++]={std::min(frames,static_cast<uint32_t>(std::max(0,metadata.samplePosition))),bytes[0],size>=2?bytes[1]:uint8_t{0},size>=3?bytes[2]:uint8_t{0}};
                else engine.meters.droppedEvents.fetch_add(1,std::memory_order_relaxed);
            }
        }
        midi.clear();rmx::Transport hostTransport;
        const bool automaticTempo=engine.params.get(rmx::Param::AutoTempo)>.5f;
        if(auto* head=getPlayHead()) if(auto position=head->getPosition()) {
            if(auto tempo=position->getBpm();automaticTempo&&tempo&&std::isfinite(*tempo)&&*tempo>=40&&*tempo<=240) { hostTransport.bpm=*tempo;hostTransport.synced=true; }
            if(auto ppq=position->getPpqPosition();ppq&&std::isfinite(*ppq))hostBeatEstimate=std::max(0.,*ppq);
            hostTransport.playing=position->getIsPlaying();
            hostTransport.beat=hostBeatEstimate;
        }
        size_t eventIndex=0;float inputPeak=0,outputPeak=0;
        auto processPart=[&](uint32_t begin,uint32_t end) {
            if(begin==end)return;
            auto transport=hostTransport;
            if(transport.synced) { if(transport.playing)transport.beat+=begin*transport.bpm/(60*getSampleRate()); }
            else {
                const auto clock=midiClock.position(static_cast<double>(sampleClock+begin)/getSampleRate());
                if(automaticTempo&&clock.synced) { transport.synced=true;transport.bpm=clock.bpm;transport.beat=clock.beat;transport.playing=clock.playing; }
            }
            std::array<rmx::Event,256> local{};size_t localCount=0;
            if(midiRollStopPending) { local[localCount++]={rmx::EventType::RollStop};midiRollStopPending=false; }
            while(eventIndex<count&&events[eventIndex].offset<end) {
                auto event=events[eventIndex++];event.offset=event.offset>begin?event.offset-begin:0;
                if(localCount<local.size())local[localCount++]=event;
                else engine.meters.droppedEvents.fetch_add(1,std::memory_order_relaxed);
            }
            engine.process(buffer.getReadPointer(0)+begin,buffer.getReadPointer(1)+begin,buffer.getWritePointer(0)+begin,buffer.getWritePointer(1)+begin,end-begin,transport,{local.data(),localCount});
            inputPeak=std::max(inputPeak,engine.meters.input.load(std::memory_order_relaxed));
            outputPeak=std::max(outputPeak,engine.meters.output.load(std::memory_order_relaxed));
        };
        uint32_t cursor=0;
        for(size_t i=0;i<clockCount;++i) {
            const auto clock=clocks[i];processPart(cursor,clock.offset);cursor=clock.offset;
            midiClock.receive(clock.status,clock.a,clock.b,static_cast<double>(sampleClock+cursor)/getSampleRate());
            if(clock.status==0xfc&&!hostTransport.synced)midiRollStopPending=true;
        }
        processPart(cursor,frames);
        engine.meters.input.store(inputPeak,std::memory_order_relaxed);engine.meters.output.store(outputPeak,std::memory_order_relaxed);
        if(hostTransport.synced&&hostTransport.playing)hostBeatEstimate=hostTransport.beat+frames*hostTransport.bpm/(60*getSampleRate());
        acknowledged.store(assets->generation,std::memory_order_release);
        sampleClock+=static_cast<uint64_t>(buffer.getNumSamples());
        // Return reset gestures to host automation from the message thread.
        for(auto p:{rmx::Param::SceneOn,rmx::Param::Low,rmx::Param::Mid,rmx::Param::High,rmx::Param::XHold,rmx::Param::Overdub,rmx::Param::Tempo,rmx::Param::AutoTempo,rmx::Param::XSource}) {
            const auto i=static_cast<size_t>(p); if(engine.params.get(p)!=raw[i]->load(std::memory_order_relaxed)) pendingValues[i].store(engine.params.get(p),std::memory_order_relaxed);
        }
    }
    void getStateInformation(juce::MemoryBlock& destination) override {
        const juce::ScopedLock guard(assetLock);
        for(size_t i=0;i<rmx::parameterCount;++i) state.values[i]=raw[i]->load();
        const auto data=state.serialize(); destination.replaceAll(data.data(),data.size());
    }
    void setStateInformation(const void* data,int bytes) override {
        if(bytes<=0) return;
        try { restore(rmx::State::parse({static_cast<const char*>(data),static_cast<size_t>(bytes)})); }
        catch(const std::exception& e) { const juce::ScopedLock lock(assetLock); assetMessage=e.what(); }
    }
    void change(rmx::Param p,float value) {
        if(auto* parameter=tree.getParameter(js(rmx::parameters[static_cast<size_t>(p)].id))) { parameter->beginChangeGesture(); parameter->setValueNotifyingHost(parameter->convertTo0to1(rmx::sanitize(p,value))); parameter->endChangeGesture(); }
    }
    void importSample(int slot,const juce::File& file) {
        auto sample=rmx::readWav(file.getFullPathName().toStdString());
        const juce::ScopedLock lock(assetLock); auto next=published.load()->bank;
        if(!rmx::sampleFitsBank(next,static_cast<size_t>(slot),sample))throw std::runtime_error("Sample would exceed this bank's 16-second total");
        next.slots[static_cast<size_t>(slot)]=std::move(sample); state.samplePaths[static_cast<size_t>(slot)]=file.getFullPathName().toStdString(); publish(std::move(next)); assetMessage="Sample installed";
        change(rmx::Param::SampleSource,1);
    }
    rmx::SamplePlayback samplePlayback(int slot) { const juce::ScopedLock lock(assetLock);return state.samplePlayback.at(static_cast<size_t>(slot)); }
    void configureSample(int slot,rmx::SamplePlayback playback) {
        if(!rmx::validSamplePlayback(static_cast<size_t>(slot),playback))throw std::runtime_error("Loop requires slot 1 and sample BPM between 70 and 200");
        const juce::ScopedLock lock(assetLock);auto next=published.load()->bank;next.slots[static_cast<size_t>(slot)].playback=playback;
        publish(std::move(next));assetMessage="Sample playback settings installed";
        change(rmx::Param::SampleSource,1);
        updateHostDisplay();
    }
    void save(const juce::File& file) { const juce::ScopedLock lock(assetLock); for(size_t i=0;i<rmx::parameterCount;++i) state.values[i]=raw[i]->load(); state.save(file.getFullPathName().toStdString()); }
    void load(const juce::File& file) { restore(rmx::State::load(file.getFullPathName().toStdString())); }
private:
    struct Assets { rmx::SampleBank bank; uint64_t generation; };
    std::vector<std::unique_ptr<Assets>> owned;
    std::atomic<const Assets*> published{};
    std::atomic<uint64_t> acknowledged{};
    uint64_t generation{};
    juce::CriticalSection assetLock;
    std::array<std::atomic<float>*,rmx::parameterCount> raw{};
    std::array<std::atomic<float>,rmx::parameterCount> pendingValues;
    std::array<std::atomic<int>,128> ccMap{};
    std::array<float,128> lastCC{};
    std::array<bool,128> pickedUp{};
    uint64_t sampleClock{};double hostBeatEstimate{};rmx::MidiClock midiClock;bool midiRollStopPending{};
    void publish(rmx::SampleBank bank) {
        state.captureSamples(bank);
        auto next=std::make_unique<Assets>(Assets{std::move(bank),++generation}); const auto* ptr=next.get(); owned.push_back(std::move(next)); published.store(ptr,std::memory_order_release);
        const auto safe=acknowledged.load(std::memory_order_acquire);
        std::erase_if(owned,[&](const auto& asset) { return asset->generation<safe; });
        for(size_t i=0;i<128;++i) ccMap[i].store(state.cc[i]);
    }
    void restore(rmx::State next) {
        auto bank=rmx::makeFactoryBank(); juce::String missing;
        for(size_t i=0;i<16;++i) if(!next.samplePaths[i].empty()) { try { bank.slots[i]=rmx::readWav(next.samplePaths[i]); } catch(...) { missing+=" "+juce::String(static_cast<int>(i+1)); } }
        next.applySamples(bank);
        const juce::ScopedLock lock(assetLock); state=std::move(next); publish(std::move(bank));
        for(size_t i=0;i<rmx::parameterCount;++i) change(static_cast<rmx::Param>(i),state.values[i]);
        assetMessage=missing.isEmpty()?"Preset restored":"Missing samples; factory sounds in slots"+missing;
    }
    void timerCallback() override {
        for(size_t i=0;i<rmx::parameterCount;++i) { const float v=pendingValues[i].exchange(std::numeric_limits<float>::quiet_NaN()); if(std::isfinite(v)) change(static_cast<rmx::Param>(i),v); }
    }
};

#include "HardwareEditor.h"
juce::AudioProcessorEditor* RMXProcessor::createEditor() { return new RMXEditor(*this); }
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new RMXProcessor; }
