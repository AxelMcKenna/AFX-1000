#include "rmx/CalibratedCutAdd.h"

namespace rmx {
void CalibratedCutAdd::process(std::span<const Stereo,32> input,std::span<Stereo,32> output) noexcept {
        std::array<Stereo,32> wet{},bypass{};bypassBlock(input,bypass);std::array<float,32> gain{};detectorBlock(input,gain);
        if(selected&&storageActive){if(initializing){resetAdd();equalizer.state={};for(auto& f:low)f.state={};for(auto& f:high)f.state={};for(unsigned i=0;i<3;++i)detector[i].c=low[i].c;configured=true;manual={};manualGain={};raw={static_cast<int>(controls[0]),static_cast<int>(controls[1]),static_cast<int>(controls[2])};lowGain=raw[2]<=123?raw[2]*.008130080997943878f:1;initializing=false;}
            std::array<std::array<int,3>,2> positions{};
            for(unsigned half=0;half<2;++half){for(unsigned i=0;i<3;++i){if(raw[i]<static_cast<int>(controls[i]))++raw[i];else if(raw[i]>static_cast<int>(controls[i]))--raw[i];}positions[half]=raw;}
            std::array<Stereo,32> lo{},hi{};low[0].process(input,lo);high[0].process(input,hi);for(unsigned i=1;i<3;++i){low[i].process(lo,lo);high[i].process(hi,hi);}
            for(unsigned i=0;i<32;++i)wet[i]={hi[i].l-lo[i].l*gain[i],hi[i].r-lo[i].r*gain[i]};equalizer.process(wet,wet);
            for(unsigned filter=0;filter<2;++filter){
                const int control=raw[filter==0?0:1];float amount=0;if(control<=123)amount=(control*-.004065040498971939f)*2+1;
                const float blendTarget=amount<.25f?amount*-4+1:0,blendStep=(blendTarget-manualGain[filter])*.03125f;
                for(unsigned i=0;i<32;++i){
                    const auto coefficient=static_cast<unsigned>((filter?0:128)+std::min(positions[i/16][filter==0?0:1],127));
                    const auto alternate=manual[filter].process(wet[i],detail::cutFilterCoefficients[coefficient]);manualGain[filter]+=blendStep;const float dry=manualGain[filter]*manualGain[filter],processed=1-dry;
                    wet[i]={wet[i].l*dry+alternate.l*processed,wet[i].r*dry+alternate.r*processed};
                }
                manualGain[filter]=blendTarget;
            }
            std::array<Stereo,32> kick{},added{};for(unsigned i=0;i<32;++i)kick[i]={lo[i].l*(gain[i]-1),lo[i].r*(gain[i]-1)};
            processAdd(wet,kick,added);
            const float target=raw[2]<=123?raw[2]*.008130080997943878f:1,delta=(target-lowGain)*.03125f;
            for(unsigned i=0;i<32;++i){lowGain=std::clamp(lowGain+delta,0.f,1.f);wet[i]={added[i].l+(wet[i].l+kick[i].l*lowGain),added[i].r+(wet[i].r+kick[i].r*lowGain)};}lowGain=target;}else std::copy(input.begin(),input.end(),wet.begin());
        if(enabled!=selected){step=-.00625f;phase=1;}else if(phase==2)step=.00625f;
        for(unsigned i=0;i<32;++i){master+=step;const auto dry=enabled?bypass[i]:input[i];output[i]={wet[i].l*master+dry.l*(1-master),wet[i].r*master+dry.r*(1-master)};}
        if(master>1-.00625f){master=1;step=0;phase=0;}
        if(master<.00625f){master=step=0;selected=enabled;phase=2;initializing=selected;}
    }

}
