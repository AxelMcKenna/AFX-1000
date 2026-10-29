#include "rmx/FactoryRelease.h"

namespace rmx {
// Preserve separate float operations in the motion state and first-order IIRs.
void FactoryRelease::process(std::span<const Stereo,32> input,std::span<Stereo,32> output,double bpm) noexcept {
    spin.record(input);
    const unsigned lever=returnFrames?1:position;
    if(returnFrames)returnFrames-=32;
    auto select=[&]{
        current=target;
        if(current==0)spin.resetState();else if(current==1)echo.resetState();else brake.resetState();
    };
    if(target!=current){
        if(lever){masterStep=-.00625f;masterPhase=1;}
        else select();
    }
    if(current==0)spin.process(input,output,lever,bpm,true,true);
    else if(current==1)echo.process(input,output,lever,bpm,true);
    else if(current==2)brake.process(input,output,lever,bpm,true);
    else std::copy(input.begin(),input.end(),output.begin());
    if(masterPhase==2)masterStep=.00625f;
    for(auto& x:output){master=std::clamp(master+masterStep,0.f,1.f);x={x.l*master,x.r*master};}
    if(master>1.f-.00625f){master=1;masterStep=0;masterPhase=0;}
    if(master<.00625f){master=masterStep=0;select();masterPhase=2;}
}
}
