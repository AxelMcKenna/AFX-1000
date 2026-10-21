#include <juce_audio_utils/juce_audio_utils.h>
#include "rmx/Engine.h"
#include "rmx/State.h"
#include "rmx/Wav.h"
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
        for(const auto& p:rmx::parameters) result.add(std::make_unique<juce::AudioParameterFloat>(juce::ParameterID(js(p.id),1),js(p.name),juce::NormalisableRange<float>(p.min,p.max,p.discrete?1.f:0.f),p.initial));
        return result;
    }
    const juce::String getName() const override { return "RMX"; }
    bool acceptsMidi() const override { return true; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override {
        const double delay=60/std::max(40.f,engine.params.get(rmx::Param::Tempo))*rmx::beatDivisions[static_cast<size_t>(engine.params.get(rmx::Param::SceneTime))];
        const double feedback=std::clamp(static_cast<double>(engine.params.get(rmx::Param::Feedback))*(.7+engine.params.get(rmx::Param::SceneResonance)*.6),.01,.96);
        // Imported 30-second samples can play four times slower at -24 semitones.
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
    }
    void releaseResources() override {}
    void processBlock(juce::AudioBuffer<float>& buffer,juce::MidiBuffer& midi) override {
        juce::ScopedNoDenormals noDenormals;
        if(buffer.getNumChannels()<2) { buffer.clear(); return; }
        for(size_t i=0;i<rmx::parameterCount;++i) engine.params.set(static_cast<rmx::Param>(i),raw[i]->load(std::memory_order_relaxed));
        const auto* assets=published.load(std::memory_order_acquire); engine.setBank(&assets->bank);
        std::array<rmx::Event,256> events{}; size_t count=0;
        for(const auto metadata:midi) {
            const auto* bytes=metadata.data; const int size=metadata.numBytes;
            if(size>=3&&(bytes[0]&0xf0)==0x90&&bytes[2]>0&&bytes[1]>=36&&bytes[1]<=39) {
                if(count<events.size()) events[count++]={rmx::EventType::Trigger,static_cast<uint8_t>(bytes[1]-36),bytes[2]/127.f,static_cast<uint32_t>(std::max(0,metadata.samplePosition))};
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
            if(size>=1&&bytes[0]==0xfa) { clockPlaying=true; clockBeat=0; lastClock=0; }
            if(size>=1&&bytes[0]==0xfb) clockPlaying=true;
            if(size>=1&&bytes[0]==0xfc) clockPlaying=false;
            if(size>=1&&bytes[0]==0xf8) {
                const auto now=sampleClock+static_cast<uint64_t>(std::max(0,metadata.samplePosition));
                if(lastClock&&now>lastClock) { const double measured=60*getSampleRate()/(24*(now-lastClock)); if(measured>=40&&measured<=240) clockBpm+=(measured-clockBpm)*.15; }
                lastClock=now; clockBeat+=1./24;
            }
        }
        midi.clear(); rmx::Transport transport;
        if(auto* head=getPlayHead()) if(auto position=head->getPosition()) {
            if(auto tempo=position->getBpm()) { transport.bpm=*tempo; transport.synced=true; }
            if(auto ppq=position->getPpqPosition()) transport.beat=std::max(0.,*ppq);
            transport.playing=position->getIsPlaying();
        }
        if(!transport.synced&&clockPlaying&&lastClock&&static_cast<double>(sampleClock)-static_cast<double>(lastClock)<getSampleRate()*.5) { transport.synced=true; transport.bpm=clockBpm; transport.beat=std::max(0.,clockBeat+(static_cast<double>(sampleClock)-static_cast<double>(lastClock))*clockBpm/(60*getSampleRate())); }
        engine.process(buffer.getReadPointer(0),buffer.getReadPointer(1),buffer.getWritePointer(0),buffer.getWritePointer(1),static_cast<uint32_t>(buffer.getNumSamples()),transport,{events.data(),count});
        acknowledged.store(assets->generation,std::memory_order_release);
        sampleClock+=static_cast<uint64_t>(buffer.getNumSamples());
        // Return reset gestures to host automation from the message thread.
        for(auto p:{rmx::Param::SceneOn,rmx::Param::Low,rmx::Param::Mid,rmx::Param::High,rmx::Param::XHold,rmx::Param::Overdub,rmx::Param::Tempo,rmx::Param::AutoTempo}) {
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
        const juce::ScopedLock lock(assetLock); auto next=published.load()->bank; next.slots[static_cast<size_t>(slot)]=std::move(sample); state.samplePaths[static_cast<size_t>(slot)]=file.getFullPathName().toStdString(); publish(std::move(next)); assetMessage="Sample installed";
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
    uint64_t sampleClock{},lastClock{}; double clockBpm{120},clockBeat{}; bool clockPlaying{};
    void publish(rmx::SampleBank bank) {
        auto next=std::make_unique<Assets>(Assets{std::move(bank),++generation}); const auto* ptr=next.get(); owned.push_back(std::move(next)); published.store(ptr,std::memory_order_release);
        const auto safe=acknowledged.load(std::memory_order_acquire);
        std::erase_if(owned,[&](const auto& asset) { return asset->generation<safe; });
        for(size_t i=0;i<128;++i) ccMap[i].store(state.cc[i]);
    }
    void restore(rmx::State next) {
        auto bank=rmx::makeFactoryBank(); juce::String missing;
        for(size_t i=0;i<16;++i) if(!next.samplePaths[i].empty()) { try { bank.slots[i]=rmx::readWav(next.samplePaths[i]); } catch(...) { missing+=" "+juce::String(static_cast<int>(i+1)); } }
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
