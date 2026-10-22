#include "rmx/Isolator.h"
#include "rmx/Engine.h"
#include "rmx/State.h"
#include <iostream>
#include <numbers>
#include <stdexcept>

using namespace rmx;
constexpr double pi=std::numbers::pi;
void require(bool condition,const char* message) {if(!condition)throw std::runtime_error(message);}
float tone(double hz,size_t frame,double rate=48000) {return .2f*static_cast<float>(std::sin(2*pi*hz*frame/rate));}
int main() {try {
    for(int mode=0;mode<4;++mode) {
        Isolator processor;processor.prepare(48000);IsolatorSettings settings;settings.mode=mode;processor.configure(settings);
        for(size_t i=0;i<48000;++i) {Stereo in{tone(237,i),tone(7300,i)};auto out=processor.process(in,{0,0,0},i/24000.);require(std::abs(out.l-in.l)<1e-6&&std::abs(out.r-in.r)<1e-6,"Neutral isolator mode changed stereo input");}
    }
    for(int choice=0;choice<4;++choice) {
        Isolator processor;processor.prepare(48000);IsolatorSettings s;s.maximum.fill(choice);s.minimum.fill(choice);processor.configure(s);
        constexpr float maximum[]{0,3,6,9},minimum[]{-6,-12,-18,-1000};
        for(float knob:{-1.f,1.f}) {
            processor.reset();const float gain=knob<0?std::pow(10.f,minimum[choice]/20):std::pow(10.f,maximum[choice]/20);
            for(size_t i=0;i<4800;++i) {auto out=processor.process({.1f,-.15f},{knob,knob,knob},0);require(std::abs(out.l-.1f*gain)<1e-6&&std::abs(out.r+.15f*gain)<1e-6,"Isolator dB endpoint differs from User settings");}
        }
    }
    {
        Isolator processor;processor.prepare(48000);IsolatorSettings s;s.mode=1;processor.configure(s);
        constexpr size_t taps[]{3000,6000,12000,24000};double unexpected=0;
        for(size_t i=0;i<25000;++i) {
            auto out=processor.process(i==0?Stereo{.2f,-.1f}:Stereo{},{1,1,1},i/24000.);
            bool atTap=false;for(size_t n=0;n<4;++n) if(i==taps[n]) {atTap=true;const float expected=.2f*.55f*std::pow(.72f,static_cast<float>(n));require(std::abs(out.l-expected)<1e-5&&std::abs(out.r+expected*.5f)<1e-5,"Cut/Add tap not at expected eighth-note multiple");}
            if(i>0&&!atTap)unexpected+=out.l*out.l+out.r*out.r;
        }
        require(unexpected<1e-8,"Cut/Add produced rhythmic gain or extra taps outside delay pattern");
    }
    {
        // A sustained bass should not be treated as a kick forever. A new
        // low-frequency transient should be attenuated by the Cut LOW control.
        Isolator processor;processor.prepare(48000);IsolatorSettings s;s.mode=1;processor.configure(s);
        double drySteady=0,wetSteady=0,dryKick=0,wetKick=0;
        for(size_t i=0;i<144000;++i) {
            const float in=tone(60,i);const auto out=processor.process({in,in},{-1,0,0},i/24000.);
            if(i>=96000) {drySteady+=in*in;wetSteady+=out.l*out.l;}
        }
        processor.reset();
        for(size_t i=0;i<12000;++i) {
            const double t=i/48000.;const float in=.6f*static_cast<float>(std::sin(2*pi*65*t)*std::exp(-t*18));
            const auto out=processor.process({in,in},{-1,0,0},i/24000.);dryKick+=in*in;wetKick+=out.l*out.l;
        }
        std::cout<<"Cut LOW steady bass energy ratio "<<wetSteady/drySteady<<", kick ratio "<<wetKick/dryKick<<'\n';
        require(wetSteady/drySteady>.95,"Cut LOW continuously suppressed sustained bass");
        require(wetKick/dryKick<.65,"Cut LOW did not detect/attenuate a kick transient");
    }
    {
        auto response=[](float mid,float hi,double hz) {
            Isolator processor;processor.prepare(48000);IsolatorSettings s;s.mode=1;processor.configure(s);double energy=0;
            for(size_t i=0;i<72000;++i) {const auto out=processor.process({tone(hz,i),tone(hz,i)},{0,mid,hi},i/24000.);if(i>=48000)energy+=out.l*out.l;}
            return energy;
        };
        const double highPassLow=response(-1,0,1000),highPassHigh=response(-1,0,18000);
        const double lowPassLow=response(0,-.7f,100),lowPassHigh=response(0,-.7f,5000);
        require(highPassHigh>highPassLow*20,"Cut MID does not high-pass the residual");
        require(lowPassLow>lowPassHigh*3,"Cut HI does not low-pass the residual");
    }
    {
        auto switches=[](float knob) {
            Isolator processor;processor.prepare(48000);IsolatorSettings s;s.mode=2;processor.configure(s);unsigned rises=0;bool previous=false;
            for(size_t i=0;i<96000;++i) {const auto out=processor.process({.2f,.2f},{knob,knob,knob},i/24000.);const bool on=out.l>.1f;if(on&&!previous)++rises;previous=on;}
            return rises;
        };
        const auto slow=switches(-.3f),fast=switches(-.9f);std::cout<<"Trans cycles / two seconds "<<slow<<" -> "<<fast<<'\n';require(fast>slow*4,"Trans rate did not follow knob position");
    }
    {
        Isolator processor;processor.prepare(48000);IsolatorSettings s;s.mode=2;processor.configure(s);
        for(size_t i=0;i<1500;++i)processor.process({.3f,-.2f},{1,1,1},i/24000.);
        double energy=0;for(size_t i=1500;i<4500;++i) {auto out=processor.process({},{1,1,1},i/24000.);energy+=out.l*out.l;}
        require(energy>200,"Band Roll did not freeze audio from control engagement");
    }
    {
        Isolator processor;processor.prepare(48000);IsolatorSettings s;s.mode=3;processor.configure(s);
        double fundamental=0,harmonic=0;
        for(size_t i=0;i<96000;++i) {
            const auto out=processor.process({tone(6000,i),tone(6000,i)},{-.2f,-.2f,-.2f},i/24000.);
            if(i>=48000) {fundamental+=out.l*std::sin(2*pi*6000*i/48000);harmonic+=out.l*std::sin(2*pi*18000*i/48000);}
        }
        require(std::abs(harmonic/fundamental)<.001,"Gate chopped individual waveform cycles instead of following an envelope");
    }
    {
        State state;state.values[static_cast<size_t>(Param::IsolateMaxMid)]=3;state.values[static_cast<size_t>(Param::AddPatternHigh)]=2;
        auto restored=State::parse(state.serialize());require(restored.values==state.values,"Advanced isolator settings did not roundtrip");
        auto legacy=State::parse("RMX_STATE 1\nparam tempo 128\n");require(legacy.values[static_cast<size_t>(Param::IsolateMinLow)]==3,"Older preset did not receive default full-kill setting");
    }
    {
        Engine engine;engine.prepare(48000,64);
        for(auto p:{Param::Low,Param::Mid,Param::High})engine.params.set(p,1);
        for(auto p:{Param::IsolateMaxLow,Param::IsolateMaxMid,Param::IsolateMaxHigh})engine.params.set(p,0);
        engine.reset();std::array<float,64> input,left,right;input.fill(.1f);
        for(int i=0;i<20;++i)engine.process(input.data(),input.data(),left.data(),right.data(),64);
        require(std::abs(left[63]-.1f*std::pow(10.f,6.f/20))<1e-5,"Default did not use factory gain endpoints");
        engine.params.set(Param::UserSettings,1);engine.process(input.data(),input.data(),left.data(),right.data(),64);
        require(std::abs(left[63]-.1f)<1e-5,"User did not restore saved gain endpoints");
        require(engine.params.get(Param::IsolateMaxLow)==0,"Default overwrote the stored User setting");
    }
    for(size_t i=0;i<parameterCount;++i) {
        const auto choices=parameterChoices(static_cast<Param>(i));const auto& info=parameters[i];
        if(!choices.empty())require(info.discrete&&info.min==0&&choices.size()==static_cast<size_t>(info.max+1),"Named host choices disagree with engine parameter range");
    }
    std::cout<<"PASS: isolator endpoints, neutral modes, additive delay timing, kick/residual separation, variable Trans rate, forward band capture, envelope gate and advanced state\n";
} catch(const std::exception& error) {std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;} }
