#pragma once
#include "Engine.h"
#include "Panel.h"
namespace rmx::panel {
template<class Read,class Write,class Send>
bool activate(const Control& c,Read read,Write write,Send send,bool shift=false) {
    const auto toggle=[&](Param p) { write(p,read(p)>.5f?0.f:1.f); };
    switch(c.kind) {
        case Kind::Toggle:
            if(shift&&c.param==Param::Overdub) send(Event{EventType::ClearSequence});
            else if(shift&&c.param==Param::XHold) toggle(Param::SamplerMute);
            else { toggle(c.param); if(c.param==Param::XHold&&read(c.param)<.5f) send(Event{EventType::RollStop}); }
            return true;
        case Kind::Choice: write(c.param,c.value); return true;
        case Kind::Pad: send(Event{EventType::Trigger,static_cast<uint8_t>(c.value)}); return true;
        case Kind::Action:
            switch(c.action) {
                case 6: send(Event{EventType::Tap}); return true;
                case 7: write(Param::AutoTempo,0); write(Param::Tempo,read(Param::Tempo)+c.value); return true;
                case 8: {
                    const int source=static_cast<int>(read(Param::SceneSource));
                    int bits=source==0?1:source==1?2:source==2?3:0; bits^=1<<static_cast<int>(c.value);
                    const float next=bits==0?3.f:bits==1?0.f:bits==2?1.f:2.f;
                    write(Param::SceneSource,next); write(Param::IsolateSource,next); return true;
                }
                case 9: write(Param::Bank,std::fmod(read(Param::Bank)+1,4)); return true;
                case 10: write(Param::ReleaseType,std::fmod(read(Param::ReleaseType)+1,3)); return true;
                default: return false;
            }
        default: return false;
    }
}
}
