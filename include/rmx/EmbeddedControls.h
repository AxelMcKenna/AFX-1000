#pragma once
#include "ControlSurface.h"
#include <array>
#include <algorithm>
#include <cmath>

namespace rmx {
// Sample at 1 kHz. Shift-register and touch I/O stay outside the audio ISR.
class EmbeddedControls {
public:
    template<class Read,class Write,class Send>
    void buttons(uint32_t pressed,Read read,Write write,Send send) noexcept {
        for(unsigned i=0;i<32;++i) {
            const bool value=(pressed>>i)&1u, previous=(stable>>i)&1u;
            if(value==previous) { counters[i]=0; continue; }
            if(++counters[i]<5) continue;
            counters[i]=0; stable^=uint32_t{1}<<i;
            if(i<static_cast<unsigned>(Button::Count)) surface.button(static_cast<Button>(i),value,read,write,send);
            else if(i==31) write(Param::UserSettings,value?1.f:0.f);
            else { const bool back=(stable>>29)&1u, brake=(stable>>30)&1u; write(Param::ReleaseType,back?0.f:brake?2.f:1.f); }
        }
    }
    template<class Write> void analog(unsigned channel,Param param,float normal,Write write) noexcept {
        if(channel>=filtered.size()||!std::isfinite(normal)) return;
        normal=std::clamp(normal,0.f,1.f);
        if(!initialized[channel]) { filtered[channel]=normal; initialized[channel]=true; }
        else filtered[channel]+=(normal-filtered[channel])*.125f;
        float value=filtered[channel];
        if(param==Param::ReleaseAmount) value=std::clamp((value-.025f)/.95f,0.f,1.f);
        if(param==Param::Low||param==Param::Mid||param==Param::High||param==Param::XPitch) if(std::abs(value-.5f)<.012f) value=.5f;
        const auto& info=parameters[static_cast<size_t>(param)];
        const float mapped=sanitize(param,info.min+value*(info.max-info.min));
        if(!sent[channel]||std::abs(mapped-last[channel])>=(info.discrete?.5f:(info.max-info.min)*.001f)||mapped==info.min||mapped==info.initial) {
            write(param,mapped); last[channel]=mapped; sent[channel]=true;
        }
    }
    template<class Write,class Send> void touch(uint8_t mask,Write write,Send send) noexcept {
        unsigned count=0,sum=0;
        for(unsigned i=0;i<8;++i) if(mask&(1u<<i)) {sum+=i;++count;}
        if(count) write(Param::XRoll,static_cast<float>(sum)/count);
        surface.touch(count>0,send);
    }
private:
    ControlSurface surface;
    uint32_t stable{};
    std::array<uint8_t,32> counters{};
    std::array<float,16> filtered{},last{};
    std::array<bool,16> initialized{},sent{};
};
}
