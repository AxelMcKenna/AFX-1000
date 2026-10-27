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
    void reset() noexcept {kick.reset();snare.reset();clap.reset();hat.reset();}
    void setControls(unsigned level,unsigned pitch) noexcept {
        kick.setControls(level,pitch);snare.setControls(level,pitch);clap.setControls(level,pitch);hat.setControls(level,pitch);
    }
    void trigger(unsigned pad,float value=1) noexcept {
        pad%=4;value=std::clamp(value,0.f,1.f);
        switch(pad){case 0:kick.trigger(value);break;case 1:snare.trigger(value);break;case 2:clap.trigger(value);break;case 3:hat.trigger(value);break;}
    }
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
        auto add=[&](auto& processor){processor.generateBlock(scratch);for(size_t i=0;i<32;++i)output[i]=output[i]+Stereo{scratch[i],scratch[i]};};
        add(kick);add(snare);add(clap);add(hat);
    }
private:
    drums::Kick kick;drums::Snare snare;drums::Clap clap;drums::Hat hat;
};
}
