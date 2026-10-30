#pragma once
#include "Dsp.h"
#include "drums/Kick.h"
#include "drums/Snare.h"
#include "drums/Clap.h"
#include "drums/Hat.h"
namespace rmx {
// Factory48k synthesis. Caller-owned spans keep processing/reset allocation-free.
class FactoryDrumSynth {
public:
    void setProfile(unsigned pad,int gain,unsigned decay,bool envelope) noexcept {
        const auto raw=static_cast<unsigned>(3-std::clamp(gain,-3,3));
        switch(pad%4){case 0:kick.setProfile(raw,decay,envelope);break;case 1:snare.setProfile(raw,decay,envelope);break;
            case 2:clap.setProfile(raw,decay,envelope);break;case 3:hat.setProfile(raw,decay,envelope);break;}
    }
    void reset() noexcept {kick.reset();snare.reset();clap.reset();hat.reset();muteMask=0;muteGain.fill(1);}
    void setControls(unsigned level,unsigned pitch) noexcept {
        kick.setControls(level,pitch);snare.setControls(level,pitch);clap.setControls(level,pitch);hat.setControls(level,pitch);
    }
    void trigger(unsigned pad,float value=1) noexcept {
        pad%=4;value=std::clamp(value,0.f,1.f);
        switch(pad){case 0:kick.trigger(value);break;case 1:snare.trigger(value);break;case 2:clap.trigger(value);break;case 3:hat.trigger(value);break;}
    }
    void setMuteMask(unsigned value) noexcept {muteMask=value&15u;}
    void stop(unsigned pad) noexcept {
        switch(pad%4){case 0:kick.stop();break;case 1:snare.stop();break;case 2:clap.stop();break;case 3:hat.stop();break;}
    }
    void process(std::span<Stereo> output,std::span<float> scratch) noexcept {
        if(scratch.size()<output.size()){std::fill(output.begin(),output.end(),Stereo{});return;}
        scratch=scratch.first(output.size());std::fill(output.begin(),output.end(),Stereo{});
        auto add=[&](auto& processor){processor.process(scratch);for(size_t i=0;i<output.size();++i){const float x=scratch[i];output[i]=output[i]+Stereo{x,x};}};
        add(kick);add(snare);add(clap);add(hat);
    }
    // The Engine owns the common source/Scene clock at48k. Do not mix this
    // generated-block entry point with process() between resets.
    void beginProcessing() noexcept {
        kick.beginProcessing();snare.beginProcessing();clap.beginProcessing();hat.beginProcessing();
    }
    void generateBlock(std::span<Stereo,32> output) noexcept {
        std::array<float,32> scratch{};std::fill(output.begin(),output.end(),Stereo{});
        auto add=[&](auto& processor,unsigned pad){
            processor.generateBlock(scratch);const float target=(muteMask&(1u<<pad))?0.f:1.f;
            for(size_t i=0;i<32;++i){
                muteGain[pad]=std::clamp(muteGain[pad]+(muteGain[pad]<target?.00625f:muteGain[pad]>target?-.00625f:0.f),0.f,1.f);
                const float sample=scratch[i]*muteGain[pad];output[i]=output[i]+Stereo{sample,sample};
            }
        };
        add(kick,0);add(snare,1);add(clap,2);add(hat,3);
    }
private:
    unsigned muteMask{};std::array<float,4> muteGain{1,1,1,1};
    drums::Kick kick;drums::Snare snare;drums::Clap clap;drums::Hat hat;
};
}
