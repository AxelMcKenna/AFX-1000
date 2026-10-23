#include "rmx/Engine.h"
#include "rmx/State.h"
#include <iostream>
#include <numbers>
#include <stdexcept>
#include <cstdlib>
#include <new>
#include <chrono>
#include <limits>

using namespace rmx;
static thread_local bool trackAllocations=false;
static thread_local size_t allocationCount=0;
void* operator new(size_t size) {if(trackAllocations)++allocationCount;if(void* p=std::malloc(size?size:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept {std::free(p);}
void* operator new[](size_t size) {return ::operator new(size);}
void operator delete[](void* p) noexcept {std::free(p);}
void require(bool ok,const char* message) {if(!ok)throw std::runtime_error(message);}
struct Rig {
    SampleBank bank;Engine engine;std::array<float,64> left{},right{};
    Rig() {engine.params.set(Param::SampleSource,1);engine.params.set(Param::XLevel,1);engine.params.set(Param::Quantize,0);engine.setBank(&bank);}
    void prepare() {engine.prepare(8000,64);}
    void run(unsigned frames,auto inspect,Transport transport={}) {
        for(unsigned offset=0;offset<frames;) {
            const auto n=std::min(64u,frames-offset);engine.process(nullptr,nullptr,left.data(),right.data(),n,transport);
            for(unsigned i=0;i<n;++i)inspect(offset+i,Stereo{left[i],right[i]});
            offset+=n;if(transport.synced&&transport.playing)transport.beat+=n*transport.bpm/(60*8000);
        }
    }
};
int main() {try {
    for(unsigned bank=0;bank<4;++bank) {
        Rig r;auto& sample=r.bank.slots[bank*4];sample.rate=8000;sample.frames.assign(160,{.2f,-.2f});sample.playback={120,true};
        r.engine.params.set(Param::Bank,static_cast<float>(bank));r.prepare();r.engine.enqueue({EventType::Trigger,0});
        r.run(8000,[](unsigned i,Stereo x){if(i>64)require(std::abs(x.l-.2f)<1e-5&&std::abs(x.r+.2f)<1e-5,"Slot 1 loop stopped or faded at a wrap");});
        for(unsigned hit=0;hit<40;++hit) {
            r.engine.enqueue({EventType::Trigger,0});r.run(64,[&](unsigned i,Stereo x){
                if(hit%2==0)require(peak(x)<1e-6,"Second loop-pad press did not stop playback");
                else if(i>=32)require(std::abs(x.l-.2f)<1e-6,"Stopped loop did not restart on the next press");
            });
        }
        r.engine.enqueue({EventType::Panic});r.run(64,[](unsigned,Stereo x){require(peak(x)<1e-6,"Panic left a sampler loop playing");});
    }
    {
        // A queued hit belongs to the source/bank selected when it was pressed.
        Rig r;r.bank.slots[0].rate=r.bank.internal[0].rate=8000;
        r.bank.slots[0].frames.assign(256,{.25f,-.25f});r.bank.internal[0].frames.assign(256,{.125f,.125f});r.prepare();
        r.engine.enqueue({EventType::Trigger,0});
        r.engine.params.set(Param::SampleSource,0);r.engine.params.set(Param::Bank,3);
        r.run(64,[](unsigned i,Stereo x){if(i>=32)require(std::abs(x.l-.25f)<1e-6&&std::abs(x.r+.25f)<1e-6,"Queued pad changed source after a bank/source selection");});
        r.engine.enqueue({EventType::Trigger,0});
        r.run(64,[](unsigned i,Stereo x){if(i>=32)require(std::abs(x.l-.375f)<1e-6&&std::abs(x.r+.125f)<1e-6,"Internal and bank voices did not retain separate assets");});
        require(r.engine.params.get(Param::SampleSource)==0&&r.engine.params.get(Param::Bank)==3,"Playing an old queued hit changed the current source selection");
    }
    {
        Rig r;r.bank.slots[8].rate=8000;r.bank.slots[8].frames.assign(160,{.2f,-.1f});r.prepare();
        r.engine.params.set(Param::Bank,2);const Event hit=r.engine.captureEvent({EventType::Trigger,0,1,17});
        r.engine.params.set(Param::SampleSource,0);r.engine.params.set(Param::Bank,0);
        r.engine.process(nullptr,nullptr,r.left.data(),r.right.data(),64,{},std::span{&hit,1});
        for(unsigned i=0;i<64;++i) {
            if(i<17)require(std::abs(r.left[i])+std::abs(r.right[i])<1e-6,"Host pad fired before its sample offset");
            if(i>=49)require(std::abs(r.left[i]-.2f)<1e-6&&std::abs(r.right[i]+.1f)<1e-6,"Host event lost its captured bank/source");
        }
    }
    {
        Rig r;r.engine.params.set(Param::SampleSource,0);auto& sample=r.bank.internal[0];
        sample.rate=8000;sample.playback={120,true};sample.frames.assign(160,{.2f,.2f});r.prepare();r.engine.enqueue({EventType::Trigger,0});
        float max=0;r.run(1000,[&](unsigned i,Stereo x){max=std::max(max,peak(x));if(i>=160)require(peak(x)<1e-6,"Internal drum incorrectly inherited bank loop mode");});
        require(max>.19f,"Internal drum was silent");
        auto factory=makeFactoryBank(8000,false);
        for(const auto& drum:factory.internal)require(!drum.frames.empty(),"Boot without SD lost an internal drum");
        for(const auto& sample:factory.slots)require(sample.frames.empty(),"Internal-only boot populated SD banks");
    }
    {
        // Both sources survive a four-beat overdub while the current bank changes.
        Rig r;r.bank.slots[0].rate=r.bank.internal[1].rate=8000;
        r.bank.slots[0].frames.assign(160,{.2f,-.2f});r.bank.internal[1].frames.assign(160,{.1f,.1f});
        r.prepare();r.engine.params.set(Param::Overdub,1);r.engine.enqueue({EventType::Trigger,0});
        r.engine.params.set(Param::SampleSource,0);r.engine.enqueue({EventType::Trigger,1});
        r.engine.params.set(Param::SampleSource,1);r.engine.params.set(Param::Bank,3);
        r.run(16000,[](unsigned,Stereo){});
        r.run(64,[](unsigned i,Stereo x){if(i>=32)require(std::abs(x.l-.3f)<1e-6&&std::abs(x.r+.1f)<1e-6,"Overdub lost bank or internal-source identity");});
        require(r.engine.meters.sequenceSteps==2,"Mixed-source overdub lost a lane");
    }
    {
        Rig r;auto& sample=r.bank.slots[0];sample.rate=8000;sample.frames.assign(160,{.2f,-.2f});sample.playback={120,true};
        r.prepare();r.engine.params.set(Param::Overdub,1);r.engine.enqueue({EventType::Trigger,0});r.run(8000,[](unsigned,Stereo){});
        r.engine.enqueue({EventType::Trigger,0});r.run(8000,[](unsigned,Stereo x){require(peak(x)<1e-6,"Loop stop was not immediate");});
        r.run(8000,[](unsigned i,Stereo x){if(i>=32)require(std::abs(x.l-.2f)<1e-6,"Recorded loop start toggled off on replay");});
        r.run(64,[](unsigned,Stereo x){require(peak(x)<1e-6,"Recorded loop stop did not replay");});
        require(r.engine.meters.sequenceSteps==2,"Loop start/stop did not record separately");
    }
    {
        Rig r;r.bank.slots[0].frames={{.4f,-.3f}};r.bank.slots[0].rate=8000;r.prepare();r.engine.enqueue({EventType::Trigger,0});
        r.run(64,[](unsigned i,Stereo x){require(i==0?std::abs(x.l-.4f)<1e-6&&std::abs(x.r+.3f)<1e-6:peak(x)<1e-6,"One-frame one-shot lost its final sample or failed to stop");});
    }
    for(unsigned slot:{1u,2u,3u,5u,15u}) {
        Rig r;auto& sample=r.bank.slots[slot];sample.rate=8000;sample.frames.assign(160,{.2f,.2f});sample.playback={120,true};
        r.engine.params.set(Param::Bank,static_cast<float>(slot/4));r.prepare();r.engine.enqueue({EventType::Trigger,static_cast<uint8_t>(slot%4)});
        r.run(1000,[](unsigned i,Stereo x){if(i>=160)require(peak(x)<1e-6,"Loop mode was accepted outside bank slot 1");});
    }
    for(double assetRate:{8000.,48000.})for(float pitch:{0.f,12.f}) {
        Rig r;auto& sample=r.bank.slots[0];sample.rate=assetRate;sample.playback={120,true};sample.frames.resize(static_cast<size_t>(assetRate*.02));
        for(size_t i=0;i<sample.frames.size();++i) {const auto value=.2f*static_cast<float>(std::sin(2*std::numbers::pi*500*i/assetRate));sample.frames[i]={value,value};}
        r.engine.params.set(Param::XPitch,pitch);r.prepare();r.engine.enqueue({EventType::Trigger,0});
        unsigned rises=0;bool positive=false;
        r.run(16000,[&](unsigned i,Stereo x){if(i>=8000){const bool next=x.l>0;if(next&&!positive)++rises;positive=next;}},Transport{180,0,true,true});
        const unsigned expected=pitch==0?500:1000;require(rises>=expected-3&&rises<=expected+3,"Loop tempo adjustment changed the requested pitch");
    }
    {
        // No-stretch playback must preserve linear interpolation without
        // windowing, latency or an initial phase offset. GCC can contract the
        // multiply/add operations differently after inlining on ARM, so allow
        // float rounding rather than requiring identical intermediate bits.
        std::array<Stereo,113> frames{};
        for(size_t i=0;i<frames.size();++i)frames[i]={static_cast<float>(i)/200,-static_cast<float>(i)/300};
        for(double step:{.25,1.,2.,6.}) {
            LoopStretch stretch;double timeline=0,expected=0;
            for(unsigned i=0;i<10000;++i) {
                const size_t first=static_cast<size_t>(expected),next=(first+1)%frames.size();
                const Stereo target=mix(frames[first],frames[next],static_cast<float>(expected-first));
                const Stereo actual=stretch.process(frames,timeline,step,step,48000,48000);
                constexpr float rounding=2*std::numeric_limits<float>::epsilon();
                require(std::abs(actual.l-target.l)<=rounding&&std::abs(actual.r-target.r)<=rounding,"Neutral loop stretch altered interpolation");
                expected=std::fmod(expected+step,static_cast<double>(frames.size()));
            }
        }
    }
    {
        // Sine pitch, playback duration and stereo relationships are checked
        // independently over both slower and faster loop tempos.
        for(double tempo:{70.,120.,180.,240.})for(float pitch:{-24.f,-12.f,0.f,12.f,24.f}) {
            Rig r;auto& sample=r.bank.slots[0];sample.rate=8000;sample.playback={120,true};sample.frames.resize(8000);
            for(size_t i=0;i<sample.frames.size();++i) {
                const float value=.2f*static_cast<float>(std::sin(2*std::numbers::pi*500*i/8000));
                sample.frames[i]={value,-value*.5f};
            }
            r.engine.params.set(Param::XPitch,pitch);r.prepare();r.engine.enqueue({EventType::Trigger,0});
            unsigned rises=0;bool positive=false;
            r.run(24000,[&](unsigned i,Stereo x){
                require(std::isfinite(x.l)&&std::abs(x.r+x.l*.5f)<1e-6,"Stretch changed stereo polarity or channel alignment");
                if(i>=8000) {const bool next=x.l>0;if(next&&!positive)++rises;positive=next;}
            },Transport{tempo,0,true,true});
            const unsigned expected=static_cast<unsigned>(1000*std::pow(2.,pitch/12.));
            require(rises>=expected-4&&rises<=expected+4,"Tempo and pitch were coupled during loop stretching");
        }
    }
    {
        Rig r;auto& sample=r.bank.slots[0];sample.rate=8000;sample.playback={120,true};sample.frames.resize(8000);
        for(size_t i=0;i<sample.frames.size();++i) {
            const float envelope=i<800?.2f:0;
            const float value=envelope*static_cast<float>(std::sin(2*std::numbers::pi*500*i/8000));
            sample.frames[i]={value,value};
        }
        for(float pitch:{-12.f,0.f,12.f}) {
            r.engine.params.set(Param::XPitch,pitch);r.prepare();r.engine.enqueue({EventType::Trigger,0});
            std::array<unsigned,16> onsets{};unsigned count=0,lastActive=0;
            r.run(30000,[&](unsigned i,Stereo x){
                if(std::abs(x.l)>.04f) {
                    if((count==0||i-lastActive>800)&&count<onsets.size())onsets[count++]=i;
                    lastActive=i;
                }
            },Transport{180,0,true,true});
            require(count==6,"Tempo did not determine the number of loop repetitions independently of pitch");
            for(unsigned i=1;i<count;++i)require(std::abs(static_cast<int>(onsets[i]-onsets[i-1])-5333)<320,"Stretched loop envelope drifted from source BPM");
        }
    }
    {
        // Four independent loop voices at mixed sample rates, extreme pitch
        // changes and changing tempos exercise bounded callback work and state.
        Rig r;
        for(unsigned bank=0;bank<4;++bank) {
            auto& sample=r.bank.slots[bank*4];sample.rate=bank%2?192000:8000;sample.playback={70+bank*40.,true};
            sample.frames.resize(bank?127+bank:1);
            for(size_t i=0;i<sample.frames.size();++i)sample.frames[i]={.02f*static_cast<float>(std::sin(i*.7)),.01f*static_cast<float>(std::cos(i*.3))};
        }
        r.prepare();for(uint8_t bank=0;bank<4;++bank)r.engine.enqueue({EventType::Trigger,0,1,0,bank,1});
        allocationCount=0;trackAllocations=true;
        for(unsigned block=0;block<1000;++block) {
            r.engine.params.set(Param::XPitch,block%2?-24.f:24.f);
            r.engine.process(nullptr,nullptr,r.left.data(),r.right.data(),64,Transport{block%2?40.:240.,0,true,true});
            for(unsigned i=0;i<64;++i)require(std::isfinite(r.left[i])&&std::isfinite(r.right[i])&&std::abs(r.left[i])<.2f&&std::abs(r.right[i])<.2f,"Loop automation produced unstable output");
        }
        trackAllocations=false;require(allocationCount==0,"Loop stretching allocated in the audio callback");
    }
    {
        Rig r;auto& sample=r.bank.slots[0];sample.rate=192000;sample.frames={{.15f,-.1f}};sample.playback={70,true};
        r.engine.params.set(Param::Tempo,240);r.engine.params.set(Param::XPitch,24);r.prepare();r.engine.enqueue({EventType::Trigger,0});
        r.run(8000,[](unsigned i,Stereo x){if(i>64)require(std::abs(x.l-.15f)<1e-6&&std::abs(x.r+.1f)<1e-6,"Large fractional loop step escaped a one-frame buffer");});
    }
    {
        // Report rather than enforce machine-dependent timing. All four loop
        // voices align together, so p99 includes the alignment callback peaks.
        Rig r;
        for(unsigned bank=0;bank<4;++bank) {
            auto& sample=r.bank.slots[bank*4];sample.rate=48000;sample.playback={120,true};sample.frames.resize(48000);
            for(size_t i=0;i<sample.frames.size();++i)sample.frames[i]={.02f*static_cast<float>(std::sin(i*.067)),.01f*static_cast<float>(std::cos(i*.071))};
        }
        r.engine.params.set(Param::XPitch,-5);r.engine.prepare(48000,64);
        for(uint8_t bank=0;bank<4;++bank)r.engine.enqueue({EventType::Trigger,0,1,0,bank,1});
        std::array<double,3000> timings{};
        for(auto& elapsed:timings) {
            const auto start=std::chrono::steady_clock::now();
            r.engine.process(nullptr,nullptr,r.left.data(),r.right.data(),64,Transport{180,0,true,true});
            elapsed=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-start).count();
        }
        std::sort(timings.begin(),timings.end());
        double total=0;for(const double value:timings)total+=value;
        std::cout<<"Four stretched loops, 48 kHz / 64: mean "<<total/timings.size()<<" us, p99 "<<timings[timings.size()*99/100]<<" us, deadline 1333.33 us\n";
    }
    {
        State state;for(unsigned bank=0;bank<4;++bank)state.samplePlayback[bank*4]={73.125+bank*30,true};
        auto restored=State::parse(state.serialize());require(restored.samplePlayback==state.samplePlayback,"Sampler mode/BPM did not roundtrip");
        SampleBank bank;restored.applySamples(bank);State captured;captured.captureSamples(bank);require(captured.samplePlayback==state.samplePlayback,"Sampler metadata did not reach assets");
        const auto old=State::parse("RMX_STATE 1\nparam tempo 128\n");for(auto playback:old.samplePlayback)require(playback==SamplePlayback{},"Old presets did not default to one-shot");
        require(old.values[static_cast<size_t>(Param::SampleSource)]==1,"Legacy preset changed from bank samples to internal drums");
        require(restored.values[static_cast<size_t>(Param::SampleSource)]==0,"New preset lost internal-source selection");
        for(const char* invalid:{"sample_mode 1 1 120","sample_mode 16 0 120","sample_mode 0 2 120","sample_mode 0 1 69","sample_mode 0 1 201","sample_mode 0 1 nan"}) {
            bool rejected=false;try{(void)State::parse(std::string("RMX_STATE 1\n")+invalid+'\n');}catch(const std::exception&){rejected=true;}require(rejected,"Invalid sampler metadata was accepted");
        }
        restored.samplePlayback[1].loop=true;bool rejected=false;
        try{restored.applySamples(bank);}catch(const std::exception&){rejected=true;}
        require(rejected&&bank.slots[1].playback.loop==false,"Invalid sampler metadata partly installed");
    }
    {
        SampleBank bank;for(auto& sample:bank.slots){sample.rate=8000;sample.frames.resize(32000);}
        require(bankDuration(bank,0)==16&&bankDuration(bank,3)==16,"Bank duration did not include all four slots");
        Sample replacement;replacement.rate=48000;replacement.frames.resize(192000);
        require(sampleFitsBank(bank,0,replacement),"Exactly sixteen seconds did not fit in a bank");
        replacement.frames.push_back({});require(!sampleFitsBank(bank,0,replacement),"Bank overflow by one frame was accepted");
        require(!sampleFitsBank(bank,16,replacement),"Invalid destination slot was accepted");
        bank.slots[0].frames.push_back({});State state;bool rejected=false;
        try{state.applySamples(bank);}catch(const std::exception&){rejected=true;}require(rejected,"Preset loaded more than sixteen seconds into a bank");
    }
    std::cout<<"PASS: sampler sources, queued hits, overdub, independent loop BPM/pitch, neutral interpolation, stereo, callback allocations, state and bank limits\n";
}catch(const std::exception& error){std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;} }
