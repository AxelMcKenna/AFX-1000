#include "rmx/Engine.h"
#include "rmx/ControlSurface.h"
#include "rmx/EmbeddedControls.h"
#include <array>
#include <iostream>
#include <stdexcept>
#include <vector>

using namespace rmx;
void require(bool ok,const char* message) { if(!ok) throw std::runtime_error(message); }
struct Rig {
    SampleBank bank; Engine engine;
    std::array<float,128> input{},left{},right{};
    Rig() { engine.params.set(Param::SampleSource,1);bank.slots[0].frames.assign(128,{.4f,.4f}); bank.slots[1].frames.assign(128,{.3f,-.3f}); engine.setBank(&bank); engine.prepare(48000,128); }
    double run(size_t frames,Transport transport={}) {
        double energy=0;
        while(frames) { const auto n=static_cast<uint32_t>(std::min(frames,input.size())); engine.process(input.data(),input.data(),left.data(),right.data(),n,transport); for(size_t i=0;i<n;++i) energy+=left[i]*left[i]+right[i]*right[i]; frames-=n; if(transport.synced&&transport.playing) transport.beat+=n*transport.bpm/(60*48000); }
        return energy;
    }
};
int main() { try {
    {
        Rig r; r.run(4800); r.engine.enqueue({EventType::Trigger,0});
        require(r.run(128)>.1,"Quantize delayed a hardware one-shot");
    }
    {
        Rig r; r.engine.params.set(Param::Overdub,1); r.engine.enqueue({EventType::Trigger,0}); r.run(128);
        require(r.engine.meters.sequenceSteps==1,"First overdub hit was not recorded");
        r.run(96000-128); require(r.run(128)>.1,"Overdub did not repeat at four beats");
        r.engine.params.set(Param::Overdub,0); require(r.run(96000)<1e-9,"Overdub off did not stop and delete playback");
        require(r.engine.meters.sequenceSteps==0,"Overdub off retained recorded hits");
    }
    {
        Rig r; r.engine.params.set(Param::Overdub,1); r.engine.enqueue({EventType::Trigger,0}); r.engine.enqueue({EventType::Trigger,1}); r.run(128);
        r.engine.enqueue({EventType::MutePad,0}); r.run(96000-128);
        require(r.run(128)>.1,"Per-pad mute removed other lanes");
        for(size_t i=0;i<128;++i) require(std::abs(r.left[i]+r.right[i])<1e-6,"Muted pad remained in loop");
        r.engine.enqueue({EventType::DeletePad,1}); r.run(96000-128); require(r.run(128)<1e-9,"Deleted lane still played");
        r.engine.enqueue({EventType::MutePad,0}); r.run(96000-128); require(r.run(128)>.1,"Muted lane could not be restored");
    }
    {
        Rig r; r.engine.params.set(Param::SceneType,2); r.engine.params.set(Param::SceneOn,1); r.engine.params.set(Param::SceneDepth,1); r.engine.params.set(Param::SceneSource,3); r.engine.reset();
        require(r.run(48000)>1,"Noise incorrectly depends on FX SOURCE");
    }
    {
        Rig r; r.input.fill(.2f); r.engine.params.set(Param::SceneSource,3); r.engine.params.set(Param::ReleaseAmount,1); r.engine.reset(); r.run(24000);
        for(auto x:r.left) require(std::abs(x-.2f)<1e-6,"Release processed an unselected source");
    }
    {
        Rig r; r.engine.params.set(Param::UserSettings,1); r.engine.params.set(Param::ReleaseKeepScene,1); r.engine.params.set(Param::ReleaseKeepIsolate,1); r.engine.params.set(Param::ReleaseKeepSampler,1);
        r.engine.params.set(Param::SceneOn,1); r.engine.params.set(Param::Low,.5f); r.engine.params.set(Param::Overdub,1); r.engine.params.set(Param::ReleaseAmount,1); r.run(128);
        r.engine.params.set(Param::ReleaseAmount,0); r.run(128);
        require(r.engine.params.get(Param::SceneOn)==1&&r.engine.params.get(Param::Low)==.5f&&r.engine.params.get(Param::Overdub)==1,"User release retention ignored");
    }
    {
        Rig r;const auto automatic=r.engine.params.get(Param::AutoTempo); r.engine.enqueue({EventType::NudgeStart,0,1}); r.run(48000); r.engine.enqueue({EventType::NudgeStop}); r.run(128);
        require(r.engine.params.get(Param::Tempo)==120&&r.engine.params.get(Param::AutoTempo)==automatic,"Nudge changed tempo settings");
        r.engine.params.set(Param::Quantize,1); r.engine.params.set(Param::XRoll,5); r.engine.enqueue({EventType::RollStart,0});
        require(r.run(10000)<1e-9,"Quantized roll started away from the beat grid");
    }
    {
        // Record off the global bar, then verify timing, bank identity, and seeks.
        Sequencer s; s.clear(); require(s.record(.75,{0,3,1}),"Sequence record failed"); int fired=0;
        s.advance(.75,true,[&](auto){++fired;}); s.advance(4.74,true,[&](auto){++fired;});
        require(fired==0,"Sequence started before its four-beat boundary");
        s.advance(4.75,true,[&](auto hit){ require(hit.bank==3,"Sequence lost bank identity"); ++fired; }); require(fired==1,"Sequence lost its relative start position");
        s.advance(.75,true,[&](auto){++fired;}); require(fired==2,"Backwards host seek stalled sequence");
    }
    {
        ControlSurface surface; ParameterStore p; std::vector<Event> events;
        auto read=[&](Param x){return p.get(x);}; auto write=[&](Param x,float v){p.set(x,v);}; auto send=[&](Event e){events.push_back(e);};
        auto edge=[&](Button b,bool down){surface.button(b,down,read,write,send);};
        edge(Button::Isolator,true);edge(Button::Isolator,false);
        require(p.get(Param::IsolateOn)==1&&p.get(Param::IsolateMode)==0,"First isolator button press did not enable the section");
        edge(Button::Isolator,true);edge(Button::Isolator,false);
        require(p.get(Param::IsolateOn)==0,"Second isolator button press did not bypass the section");
        edge(Button::GateDrive,true);edge(Button::GateDrive,false);
        require(p.get(Param::IsolateOn)==1&&p.get(Param::IsolateMode)==3,"Selecting another isolator mode did not enable it");
        edge(Button::Bank,true); edge(Button::Clap,true); edge(Button::Clap,false); edge(Button::Bank,false);
        require(p.get(Param::Bank)==2&&p.get(Param::SampleSource)==1&&events.empty(),"Bank chord did not silently select bank samples");
        edge(Button::Bank,true);edge(Button::Clap,true);edge(Button::Clap,false);edge(Button::Bank,false);
        require(p.get(Param::SampleSource)==0&&events.size()==1&&events.back().type==EventType::Trigger&&events.back().pad==2,"Repeated bank chord did not return to the internal drum");
        edge(Button::Hold,true);edge(Button::HiHat,true);edge(Button::HiHat,false);edge(Button::Hold,false);
        require(events.back().type==EventType::SelectPad&&events.back().pad==3&&p.get(Param::XHold)==0,"Hold+pad did not select silently without latching Hold");
        surface.touch(true,send);require(events.back().type==EventType::RollStart&&events.back().pad==3,"Silent selection did not select the strip's drum");surface.touch(false,send);
        edge(Button::Overdub,true); edge(Button::Overdub,false); require(p.get(Param::Overdub)==1,"Overdub click failed");
        edge(Button::Overdub,true); edge(Button::Kick,true); edge(Button::Kick,false); edge(Button::Overdub,false);
        require(events.back().type==EventType::DeletePad&&p.get(Param::Overdub)==1,"Delete chord toggled recording");
        edge(Button::Hold,true); edge(Button::Snare,true); edge(Button::Snare,false); edge(Button::Hold,false);
        require(events.back().type==EventType::MutePad&&p.get(Param::XHold)==0,"Mute chord toggled hold");
        edge(Button::NudgePlus,true); edge(Button::NudgePlus,false); require(events.back().type==EventType::NudgeStop,"Nudge release was lost");
        edge(Button::Roll,true); edge(Button::Roll,false); edge(Button::Kick,true); edge(Button::Kick,false);
        require(p.get(Param::XSource)==0&&events.back().type==EventType::Trigger,"Pad did not return to samples from input roll");
    }
    {
        // Live roll captures the audio after the touch and keeps that window.
        Rig r; r.engine.params.set(Param::XSource,1); r.engine.params.set(Param::XLevel,1); r.engine.params.set(Param::Quantize,0); r.engine.params.set(Param::XRoll,0); r.engine.reset();
        r.input.fill(.1f); r.run(4800); r.input.fill(.3f); r.engine.enqueue({EventType::RollStart,0}); r.run(1500);
        r.input.fill(0); require(r.run(3000)>100,"Input roll recaptured silence or sampled pre-touch audio");
        r.engine.enqueue({EventType::RollStop}); require(r.run(2400)<40,"Input roll release exceeded its fade envelope");
        require(r.run(128)<1e-4,"Input roll remained latched without Hold");
    }
    {
        Rig r; r.input.fill(.2f); r.engine.params.set(Param::SceneSource,0); r.engine.params.set(Param::ReleaseType,2); r.engine.params.set(Param::ReleaseTime,.125f); r.engine.params.set(Param::ReleaseAmount,1); r.engine.reset(); r.run(24000);
        r.engine.enqueue({EventType::Trigger,1}); require(r.run(128)>.1,"Release muted the unselected X-Pad bus");
        for(size_t i=0;i<128;++i) require(std::abs(r.left[i]+r.right[i])<1e-6,"Release left the selected dry input audible");
    }
    {
        EmbeddedControls scanner; ParameterStore p; std::vector<Event> events;
        auto read=[&](Param x){return p.get(x);}; auto write=[&](Param x,float v){p.set(x,v);}; auto send=[&](Event e){events.push_back(e);};
        const auto kick=uint32_t{1}<<static_cast<unsigned>(Button::Kick);
        for(int i=0;i<4;++i) scanner.buttons(kick,read,write,send);
        require(events.empty(),"Contact bounce triggered a pad"); scanner.buttons(0,read,write,send);
        for(int i=0;i<5;++i) scanner.buttons(kick,read,write,send);
        require(events.size()==1&&events[0].type==EventType::Trigger,"Debounced pad edge was lost");
        scanner.analog(0,Param::Low,.5f,write); require(p.get(Param::Low)==0,"Center detent was not neutral");
        scanner.analog(1,Param::ReleaseAmount,0,write); require(p.get(Param::ReleaseAmount)==0,"Lever endpoint did not release");
        scanner.touch(1u<<6,write,send); require(p.get(Param::XRoll)==6&&events.back().type==EventType::RollStart,"Touch strip position/start failed");
        scanner.touch(0,write,send); require(events.back().type==EventType::RollStop,"Touch disconnect did not release");
    }
    {
        Rig r; r.engine.params.set(Param::AutoTempo,1); r.engine.enqueue({EventType::Tap}); r.run(24000);
        r.engine.enqueue({EventType::Tap}); r.run(26400); r.engine.enqueue({EventType::Tap}); r.run(128);
        require(std::abs(r.engine.params.get(Param::Tempo)-60/.525)<.01,"Tap did not average recent intervals");
        require(r.engine.params.get(Param::AutoTempo)==0,"Tap did not leave Auto mode");
    }
    {
        ControlSurface surface; ParameterStore p; std::vector<Event> events;
        auto read=[&](Param x){return p.get(x);}; auto write=[&](Param x,float v){p.set(x,v);}; auto send=[&](Event e){events.push_back(e);};
        auto edge=[&](Button b,bool down){surface.button(b,down,read,write,send);};
        edge(Button::NudgePlus,true); edge(Button::Tap,true); edge(Button::NudgePlus,false);
        require(events.back().type==EventType::NudgeStop,"Tap/Nudge chord left Nudge latched");
        edge(Button::Tap,false); edge(Button::Tap,true); edge(Button::NudgePlus,true); edge(Button::NudgePlus,false); edge(Button::Tap,false);
        require(p.get(Param::Tempo)==121&&events.back().type==EventType::NudgeStop,"Tap+Nudge did not enter manual BPM");
    }
    std::cout<<"PASS: immediate one-shots, four-beat overdub, lane mute/delete, noise, release routing/retention, nudge, seeks, physical button chords\n";
} catch(const std::exception& e) { std::cerr<<"FAIL: "<<e.what()<<'\n'; return 1; } }
