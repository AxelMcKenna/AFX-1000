#pragma once
#include "Sample.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <memory_resource>
#include <span>
#include <vector>

namespace rmx {
// Measured default-profile Release Echo at 48 kHz.
class CalibratedReleaseEcho {
public:
    void prepare() {owned.assign(589824,{});line=owned;resetState();}
    void attach(std::span<Stereo> storage) noexcept {line=storage;resetState();}
    void resetState() noexcept {
        write=0;warm=age=0;active=false;direct=1;wet=ready=0;gates={};period=24000;
        requested=returnFrames=0;timeGain=1;previousFeedback=0;limits={20000,10000,5000};
    }
    void process(std::span<const Stereo,32> input,std::span<Stereo,32> output,unsigned raw,double bpm=120,bool leverSmoothed=false) noexcept {
        const unsigned requestedRaw=raw;
        if(!leverSmoothed){if(!raw&&requested)returnFrames=160;if(returnFrames){raw=1;returnFrames-=32;}}
        requested=requestedRaw;
        const bool on=raw>0;const unsigned region=raw<=109?0:raw<=209?1:2;
        const unsigned target=on?static_cast<unsigned>(std::floor(static_cast<float>(std::floor(60000/std::clamp(bpm,40.,240.)))*std::array<float,3>{1,.5f,.25f}[region]))*48:24000;
        std::array<Stereo,32> delayed{};
        const auto read=(write+line.size()-period)%line.size();
        for(size_t i=0;i<32;++i)delayed[i]=line[(read+i)%line.size()];
        const bool valid=warm>=period*2;if(warm<0x180000)warm+=64;
        if(on&&!active){warm=age=0;gates={1,1,1};period=target;}
        if(on)limits[region]=target-160;
        const float step=on?.00625f:-.00625f;
        const float timeStep=target==period?.00625f:-.00625f;
        const auto gateSteps=std::array<float,3>{age>=limits[0]?-.00625f:.00625f,age>=limits[1]?-.00625f:.00625f,age>=limits[2]?-.00625f:.00625f};
        const float feedbackTarget=on?.7f:previousFeedback;const float feedbackStep=(feedbackTarget-previousFeedback)*.00625f;float feedback=previousFeedback;bool clearFeedback=false;
        for(size_t i=0;i<32;++i){
            if(direct-step>1.f)clearFeedback=true;
            direct=std::clamp(direct-step,0.f,1.f);wet=std::clamp(wet+step,0.f,1.f);ready=std::clamp(ready+step,0.f,1.f);
            timeGain+=timeStep;if(timeGain<0){timeGain=0;period=target;}else timeGain=std::min(timeGain,1.f);
            for(size_t j=0;j<3;++j)gates[j]=std::clamp(gates[j]+gateSteps[j],0.f,1.f);
            feedback+=feedbackStep;
            const float capture=gates[region]*(ready*timeGain);
            const float loop=(valid?1.f:0.f)*timeGain*feedback;
            const auto x=input[i],tap=delayed[i];
            line[write]={((x.l*capture)+(tap.l*loop))*ready,((x.r*capture)+(tap.r*loop))*ready};
            output[i]={x.l*direct+line[write].l*wet,x.r*direct+line[write].r*wet};
            write=(write+1)%line.size();
        }
        previousFeedback=clearFeedback?0.f:feedbackTarget;active=on;age=std::min(age+32,576000u);
    }
private:
    std::pmr::vector<Stereo> owned;std::span<Stereo> line;size_t write{};unsigned warm{},age{},period{24000},requested{},returnFrames{};
    std::array<unsigned,3> limits{20000,10000,5000};std::array<float,3> gates{};
    float direct{1},wet{},ready{},timeGain{1},previousFeedback{};bool active{};
};
}
