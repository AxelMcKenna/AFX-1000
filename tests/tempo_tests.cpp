#include "rmx/TempoTracker.h"
#include "rmx/MidiClock.h"
#include <array>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {
constexpr double pi=3.14159265358979323846;
void require(bool value,const char* message) { if(!value) throw std::runtime_error(message); }
void rhythm(rmx::TempoTracker& tracker,double rate,double seconds,double bpm,bool stereo=false,bool busy=false,double offset=.173) {
    const int count=static_cast<int>(seconds*rate);
    for(int i=0;i<count;++i) {
        const double time=i/rate-offset,period=60/bpm;
        const double phase=time<0?period:std::fmod(time,period);
        float left=static_cast<float>(std::sin(2*pi*70*phase)*std::exp(-phase*40))*.7f;
        if(busy&&time>=0) {
            const double hat=std::fmod(time,period*.5);
            left+=static_cast<float>(std::sin(2*pi*7133*hat)*std::exp(-hat*220))*.11f;
            left+=static_cast<float>(std::sin(2*pi*181*time))*.035f;
        }
        tracker.process(left,stereo?-left:left);
    }
}
}
int main() {
    try {
        for(double rate:{44100.,48000.,96000.}) for(double expected:{90.,120.,128.,150.,173.}) {
            rmx::TempoTracker tracker; tracker.prepare(rate);
            rhythm(tracker,rate,14,expected,true,true);
            const double expectedPhase=std::fmod((14-.173)*expected/60,1.);
            const double error=std::abs(std::remainder(tracker.phase()-expectedPhase,1.));
            std::cout<<rate<<" Hz, "<<expected<<" BPM -> "<<tracker.bpm()<<", confidence "<<tracker.certainty()<<", phase error "<<error<<" beats\n";
            require(std::abs(tracker.bpm()-expected)<2.5,"Stereo busy rhythm BPM mismatch");
            require(tracker.phaseLocked(),"Periodic rhythm did not acquire beat phase");
            require(error<.1,"Beat phase outside 0.1 beat tolerance");
            require(std::abs(tracker.phaseSlew(0))<=.25,"Phase slew exceeds bounded rate");
        }
        // An incremental lag sweep must not compare a faster pulse's weaker
        // window against a later octave peak and lock plain kicks at half time.
        for(double offset:{0.,.07,.173,.31}) {
            rmx::TempoTracker plain;plain.prepare(48000);rhythm(plain,48000,14,173,false,false,offset);
            require(std::abs(plain.bpm()-173)<2.5,"Plain fast kicks locked to a half-time octave");
        }
        rmx::TempoTracker tracker; tracker.prepare(48000);
        rhythm(tracker,48000,10,120);
        require(tracker.certainty()>.18f,"Initial rhythm did not lock");
        for(int i=0;i<48000;++i) tracker.process(0,0);
        require(tracker.certainty()==0&&!tracker.phaseLocked(),"Silence retained old beat lock");
        rhythm(tracker,48000,7,150);
        require(std::abs(tracker.bpm()-150)<2.5,"Silence-to-new-tempo reacquisition failed");
        rhythm(tracker,48000,7,90);
        require(std::abs(tracker.bpm()-90)<2.5,"Direct tempo change did not reacquire within seven seconds");
        tracker.reset();
        for(int i=0;i<48000*8;++i) {
            const float tone=static_cast<float>(std::sin(2*pi*220*i/48000.))*.2f;
            tracker.process(tone,-tone);
        }
        require(tracker.certainty()<.18f,"Steady tone reported rhythmic lock");
        tracker.prepare(std::numeric_limits<double>::quiet_NaN());
        for(int i=0;i<48000;++i) tracker.process(std::numeric_limits<float>::infinity(),std::numeric_limits<float>::quiet_NaN());
        require(std::isfinite(tracker.bpm())&&tracker.certainty()==0,"Invalid input corrupted tracker");
        {
            rmx::MidiClock clock;
            clock.receive(0xfa,0,0,10);
            clock.receive(0xf8,0,0,10);
            require(clock.position(10).synced&&clock.position(10).beat==0,"MIDI Start did not align on its first pulse");
            clock.reset();clock.receive(0xfa,0,0,10);
            for(int tick=0;tick<=96;++tick) {
                const double time=10+tick*60./(24*128)+(tick%3-1)*.0004;
                clock.receive(0xf8,0,0,time);
            }
            auto position=clock.position(10+96*60./(24*128));
            require(position.synced&&position.playing,"MIDI clock failed to synchronize");
            require(std::abs(position.bpm-128)<1,"MIDI clock jitter changed BPM");
            require(std::abs(position.beat-4)<.01,"MIDI Start first clock was not beat zero");
            const double lastTickTime=10+96*60./(24*128);
            const auto beforeLastTick=clock.position(lastTickTime-.01);
            require(std::abs(beforeLastTick.beat-(4-.01*128/60))<.01,"Block-start query failed to project back from later MIDI tick");
            clock.receive(0xfc,0,0,12);
            require(clock.position(20).synced&&!clock.position(20).playing,"MIDI Stop failed to hold transport stopped");
            clock.receive(0xf2,16,0,20);
            require(clock.position(20).beat==4,"Song Position Pointer uses wrong sixteenth-note units");
            clock.reset();clock.receive(0xfa,0,0,1);
            for(int group=0;group<30;++group)for(int tick=0;tick<4;++tick)clock.receive(0xf8,0,0,1+group*4*60./(24*120));
            require(std::abs(clock.position(1+29*4*60./(24*120)).bpm-120)<.1,"Batched MIDI timestamps changed tempo");
            require(!clock.position(20).synced,"MIDI clock timeout stayed synchronized");
            clock.reset();require(!clock.position(20).synced,"MIDI source reset retained old transport");
            rmx::MidiStreamParser parser;std::array<std::array<uint8_t,3>,4> messages{};size_t count=0;
            for(uint8_t value:std::array<uint8_t,9>{0xf2,16,0xf8,0,0x90,36,127,37,64})
                parser.byte(value,[&](uint8_t status,uint8_t a,uint8_t b){if(count<messages.size())messages[count++]={status,a,b};});
            require(count==4&&messages[0][0]==0xf8&&messages[1]==std::array<uint8_t,3>{0xf2,16,0},"Real-time clock damaged Song Position Pointer");
            require(messages[3]==std::array<uint8_t,3>{0x90,37,64},"MIDI running status lost second note");
        }
        std::cout<<"PASS: tempo, phase, stereo, silence, tempo changes, tone rejection, invalid audio, MIDI clock and parser\n";
    } catch(const std::exception& error) { std::cerr<<"FAIL: "<<error.what()<<'\n';return 1; }
}
