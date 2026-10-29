#pragma once
#include "Sample.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <memory_resource>
#include <span>
#include <vector>

namespace rmx {
// Measured default-profile Back Spin: bounded history and float32 motion state.
class CalibratedReleaseSpin {
public:
    void prepare(){ownedHistory.assign(196608,{});ownedSnapshot.assign(196608,{});history=ownedHistory;snapshot=ownedSnapshot;write=historyFrames=0;resetState();}
    void attach(std::span<Stereo> raw,std::span<Stereo> work) noexcept {history=raw;snapshot=work;write=historyFrames=0;resetState();}
    void resetHistoryPosition() noexcept {write=historyFrames=0;}
    void record(std::span<const Stereo,32> input) noexcept {for(auto x:input){history[write]=x;write=(write+1)%history.size();historyFrames=std::min(historyFrames+1,history.size());}}
    void resetState() noexcept {
        anchor=read=copied=requested=returnFrames=0;speed=carry=delta=wet=0;direct=fade=1;active=false;states={};
    }
    void process(std::span<const Stereo,32> input,std::span<Stereo,32> output,unsigned raw,double bpm=120,bool recorded=false,bool leverSmoothed=false) noexcept {
        if(!recorded)record(input);
        const unsigned requestedRaw=raw;
        if(!leverSmoothed){if(!raw&&requested)returnFrames=160;if(returnFrames){raw=1;returnFrames-=32;}}
        requested=requestedRaw;
        const bool on=raw>0;const float beat=static_cast<float>(std::floor(60000/std::clamp(bpm,40.,240.)))*48;
        const unsigned region=raw<=109?0:raw<=209?1:2;const float duration=std::array<float,3>{8,2,1}[region];
        if(on&&!active){anchor=write;anchorFrames=historyFrames;read=copied=0;speed=carry=0;delta=(1.f/(beat*.32f))*8.f;fade=0;}
        if(on){
            if(delta>0)delta=(1.f/(beat*.32f))*8.f;
            else if(delta<0)delta=(-1.f/(beat*(duration-.32f)))*8.f;
        }
        const size_t limit=static_cast<size_t>(beat*2)-160;
        // Snapshot only the reachable history, copied ahead of the read head.
        const auto needed=std::min(snapshot.size(),limit+1024);
        for(unsigned i=0;i<320&&copied<needed;++i,++copied)snapshot[copied]=copied<anchorFrames?history[(anchor+history.size()-1-copied)%history.size()]:Stereo{};
        const float fadeStep=read>=limit?-.03125f:fade==1?0:.03125f;
        std::array<Stereo,32> played{};std::array<float,32> feedback{},numerator{};
        for(size_t i=0;i<32;++i){
            if(speed<0){speed=carry=delta=0;}
            const float old=speed;
            float gain;
            if(old<0.2834848463535309f){const double s=old;gain=static_cast<float>((1-(s+s))*((s*18.1651513899117)*s));}
            else if(old<1){const double s=old;const double first=s*3;gain=static_cast<float>((s*s)*s+(first-first*s));}
            else gain=old*.02f+.98f;
            const size_t index=std::min(read,snapshot.size()-2);
            const auto value=Stereo{read? snapshot[index-1].l:(historyFrames==history.size()||write?history[0].l:0.f),snapshot[index].r};
            played[i]={value.l*gain,value.r*gain};
            const unsigned integral=static_cast<unsigned>(old);carry+=(old-static_cast<float>(integral));
            unsigned advance=integral;if(carry>=1){carry-=1;++advance;}read+=advance;
            const float increment=(delta<0&&old<=0.2823529541492462f)?-3.1609244615538046e-5f:delta;
            speed=old+increment;
            if(speed>=8)delta=(-1.f/(beat*(duration-.32f)))*8.f;
            if(speed==0){feedback[i]=-1;numerator[i]=0;}
            else if(speed>0&&speed<1){feedback[i]=speed+speed-1;numerator[i]=(feedback[i]+1)*.5f;}
            else {feedback[i]=1;numerator[i]=1;}
        }
        for(size_t i=0;i<32;++i){
            auto value=played[i];
            for(auto& state:states){
                const float wl=value.l-feedback[i]*state.l,wr=value.r-feedback[i]*state.r;
                value={numerator[i]*wl+numerator[i]*state.l,numerator[i]*wr+numerator[i]*state.r};
                state={std::clamp(wl,-2.f,2.f),std::clamp(wr,-2.f,2.f)};
            }
            played[i]=value;
        }
        const float step=on?.00625f:-.00625f;
        for(size_t i=0;i<32;++i){
            fade+=fadeStep;direct=std::clamp(direct-step,0.f,1.f);wet+=step;
            if(wet<0){wet=0;speed=carry=delta=0;read=0;}else wet=std::min(wet,1.f);
            const float amount=fade*wet;
            output[i]={input[i].l*direct+played[i].l*amount,input[i].r*direct+played[i].r*amount};
        }
        if(fade>=1)fade=1;else if(fade<=0){fade=0;read=0;}
        active=on;
    }
private:
    std::pmr::vector<Stereo> ownedHistory,ownedSnapshot;std::span<Stereo> history,snapshot;size_t write{},historyFrames{},anchorFrames{},anchor{},read{},copied{};unsigned requested{},returnFrames{};
    std::array<Stereo,2> states{};float speed{},carry{},delta{},direct{1},wet{},fade{1};bool active{};
};
}
