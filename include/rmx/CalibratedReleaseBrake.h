#pragma once
#include "Sample.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <memory_resource>
#include <span>
#include <vector>

namespace rmx {
// Measured default-profile 48 kHz Vinyl Brake playback.
class CalibratedReleaseBrake {
public:
    void prepare(){owned.assign(589824,{});line=owned;resetState();}
    void attach(std::span<Stereo> storage) noexcept {line=storage;resetState();}
    void resetState() noexcept {
        write=read=requested=returnFrames=0;fraction=speed=delta=wet=0;direct=1;active=recording=false;states={};
    }
    void process(std::span<const Stereo,32> input,std::span<Stereo,32> output,unsigned raw,double bpm=120,bool leverSmoothed=false) noexcept {
        const unsigned requestedRaw=raw;
        if(!leverSmoothed){if(!raw&&requested)returnFrames=160;if(returnFrames){raw=1;returnFrames-=32;}}
        requested=requestedRaw;
        const bool on=raw>0;
        if(on&&!active){write=read=0;fraction=0;speed=1;delta=0;recording=true;}
        if(recording){for(size_t i=0;i<32;++i)line[(write+i)%line.size()]=input[i];write=(write+32)%line.size();}
        if(on&&speed>0){
            const unsigned region=raw<=109?0:raw<=209?1:2;
            const float beat=static_cast<float>(std::min(1500.,std::floor(60000/std::clamp(bpm,40.,240.))))*48;
            delta=speed<.125f?4.287424417270813e-6f:1.f/(beat*std::array<float,3>{16,4,.75f}[region]);
            delta=std::clamp(delta,0.f,1.f);
        }
        std::array<Stereo,32> played{};
        for(size_t i=0;i<32;++i){
            const auto a=line[read],b=line[(read+1)%line.size()];
            Stereo value{a.l*(1-fraction)+b.l*fraction,a.r*(1-fraction)+b.r*fraction};
            fraction+=speed;if(fraction>=1){fraction-=1;read=(read+1)%line.size();}
            float feedback{},numerator{};
            if(speed==0){feedback=-1;numerator=0;}
            else if(speed<1){feedback=speed+speed-1;numerator=(feedback+1)*.5f;}
            else {feedback=1;numerator=1;}
            for(auto& stage:states){
                const float wl=value.l-feedback*stage.l,wr=value.r-feedback*stage.r;
                value={numerator*wl+numerator*stage.l,numerator*wr+numerator*stage.r};
                stage={std::clamp(wl,-2.f,2.f),std::clamp(wr,-2.f,2.f)};
            }
            float gain=0;
            if(speed>.01f){
                if(speed<=.05f)gain=speed*12.5f-.125f;
                else if(speed<=.125f)gain=.5f;
                else if(speed<1)gain=speed*0.5714285969734192f+0.4285714328289032f;
                else gain=1;
            }
            played[i]={value.l*gain,value.r*gain};
            speed-=on?delta:0;if(speed<=0){speed=0;}
        }
        const float step=on?.00625f:-.00625f;
        for(size_t i=0;i<32;++i){
            direct=std::clamp(direct-step,0.f,1.f);wet+=step;
            if(wet<0){wet=0;speed=fraction=delta=0;recording=false;}else wet=std::min(wet,1.f);
            output[i]={input[i].l*direct+played[i].l*wet,input[i].r*direct+played[i].r*wet};
        }
        active=on;
    }
private:
    std::pmr::vector<Stereo> owned;std::span<Stereo> line;size_t write{},read{};unsigned requested{},returnFrames{};
    std::array<Stereo,2> states{};float fraction{},speed{},delta{},direct{1},wet{};bool active{},recording{};
};
}
