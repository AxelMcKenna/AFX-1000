#include "rmx/Engine.h"
#include "rmx/EmbeddedControls.h"
#include "rmx/State.h"
#include <iostream>
#include <stdexcept>
#include <vector>

using namespace rmx;
void require(bool ok,const char* message) {if(!ok)throw std::runtime_error(message);}
struct Rig {
    SampleBank bank;Engine engine;
    std::array<float,64> input{},left{},right{};
    Rig() {
        engine.params.set(Param::XLevel,1);engine.params.set(Param::Quantize,0);engine.params.set(Param::UserSettings,1);
        bank.internal[0].rate=8000;bank.internal[0].frames={{.25f,-.25f}};engine.setBank(&bank);
    }
    void prepare() {engine.prepare(8000,64);}
    void run(unsigned frames,auto feed,auto inspect,Transport transport={}) {
        for(unsigned offset=0;offset<frames;) {
            const unsigned n=std::min(64u,frames-offset);
            for(unsigned i=0;i<n;++i)input[i]=feed(offset+i);
            engine.process(input.data(),input.data(),left.data(),right.data(),n,transport);
            for(unsigned i=0;i<n;++i)inspect(offset+i,Stereo{left[i],right[i]});
            offset+=n;if(transport.synced&&transport.playing)transport.beat+=n*transport.bpm/(60*8000);
        }
    }
    std::vector<unsigned> hits(unsigned frames,Transport transport={}) {
        std::vector<unsigned> result;
        run(frames,[](unsigned){return 0.f;},[&](unsigned frame,Stereo x){if(peak(x)>.1f)result.push_back(frame);},transport);
        return result;
    }
};
int main() {try {
    // Measure emitted audio, including every triplet/dotted option and each
    // physical position, rather than only comparing the division lookup table.
    constexpr std::array<double,16> beats{1./32,1./24,1./16,1./12,1./8,1./6,1./4,1./3,1./2,2./3,3./4,1,3./2,2,4,8};
    for(unsigned choice=0;choice<beats.size();++choice) {
        Rig r;const unsigned position=choice%8;
        r.engine.params.set(Param::XRoll,static_cast<float>(position));
        r.engine.params.set(static_cast<Param>(static_cast<unsigned>(Param::XPadBeat1)+position),static_cast<float>(choice));
        r.prepare();r.engine.enqueue({EventType::RollStart,0});
        const double period=4000*beats[choice];const auto hits=r.hits(static_cast<unsigned>(std::ceil(period*2.25)));
        require(hits.size()==3&&hits[0]==0,"Assigned X-Pad beat produced the wrong number of repeats");
        require(std::abs(hits[1]-period)<=1.01&&std::abs(hits[2]-2*period)<=2.01,"Assigned X-Pad repeat timing is wrong");
    }
    {
        Rig r;r.engine.params.set(Param::XPadBeat1,15);r.engine.params.set(Param::XRoll,0);r.engine.params.set(Param::UserSettings,0);
        r.prepare();r.engine.enqueue({EventType::RollStart,0});const auto hits=r.hits(563);
        require(hits==std::vector<unsigned>{0,250,500},"Default used the saved User assignment");
        // Selecting User restores the saved eight-beat assignment.
        r.engine.params.set(Param::UserSettings,1);r.prepare();r.engine.enqueue({EventType::RollStart,0});
        require(r.hits(1000)==std::vector<unsigned>{0},"User did not restore its saved assignment");
    }
    {
        Rig r;r.engine.params.set(Param::Quantize,1);r.engine.params.set(Param::XRoll,3);r.engine.params.set(Param::XPadBeat4,7);
        r.prepare();r.engine.enqueue({EventType::RollStart,0});const auto hits=r.hits(1000,{120,.1,true,true});
        require(hits==std::vector<unsigned>{934},"Quantized triplet did not start on the host beat grid");
    }
    {
        Rig r;EmbeddedControls controls;
        r.engine.params.set(Param::XPadBeat7,5);r.prepare();
        auto write=[&](Param p,float v){r.engine.params.set(p,v);};auto send=[&](Event e){r.engine.enqueue(e);};
        controls.touch(1u<<6,write,send);const auto hits=r.hits(1500);
        require(hits.size()==3&&hits[0]==0&&hits[1]==667&&hits[2]==1334,"Embedded touch did not use its User beat assignment");
        controls.touch(0,write,send);require(r.hits(1500).empty(),"Touch release left assigned sample repeats running");
    }
    {
        Rig r;r.engine.params.set(Param::Tempo,40);r.engine.params.set(Param::XSource,1);r.engine.params.set(Param::XRoll,7);r.engine.params.set(Param::XPadBeat8,15);
        r.prepare();r.engine.enqueue({EventType::RollStart,0});
        // Eight beats at 40 BPM = 12 seconds, exceeding the former 8-second buffer.
        r.run(96000,[](unsigned frame){return frame<48000?.1f:.3f;},[](unsigned,Stereo){});
        r.run(96000,[](unsigned){return 0.f;},[](unsigned frame,Stereo x){
            if(frame>=1000&&frame<1020)require(std::abs(x.l-.1f)<1e-5&&std::abs(x.r-.1f)<1e-5,"Long input roll lost its first half");
            if(frame>=60000&&frame<60020)require(std::abs(x.l-.3f)<1e-5&&std::abs(x.r-.3f)<1e-5,"Long input roll was truncated or recaptured");
        });
    }
    {
        State state;for(unsigned position=0;position<8;++position)state.values[static_cast<size_t>(Param::XPadBeat1)+position]=static_cast<float>(15-position);
        const auto copy=State::parse(state.serialize());
        for(unsigned position=0;position<8;++position)require(copy.values[static_cast<size_t>(Param::XPadBeat1)+position]==15-position,"Preset lost an X-Pad assignment");
        const auto legacy=State::parse("RMX_STATE 1\nparam x_roll 3\n");
        require(xPadDivision(legacy.values)==.5,"Legacy strip position changed division");
    }
    std::cout<<"PASS: 16 X-Pad divisions, Default/User, quantized triplets, embedded touch, 12-second input capture and preset recall\n";
}catch(const std::exception& error){std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;} }
