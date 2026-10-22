#pragma once
#include "Engine.h"

namespace rmx {
// Physical button edges after debouncing. Shared by firmware and controller
// adapters, with no dependency on a window system, GPIO driver or MIDI library.
enum class Button : uint8_t {
    Quantize, Auto, Tap, NudgeMinus, NudgePlus, Input, XPad,
    Isolator, CutAdd, TransRoll, GateDrive, Bank, Roll,
    Kick, Snare, Clap, HiHat, Overdub, Hold,
    BpfEcho, Echo, Noise, SpiralUp, ReverbUp, HpfEcho, LpfEcho, CrushEcho, SpiralDown, ReverbDown,
    Count
};
class ControlSurface {
public:
    template<class Read,class Write,class Send>
    void button(Button button,bool down,Read read,Write write,Send send) noexcept {
        const auto bit=uint64_t{1}<<static_cast<unsigned>(button);
        if(bool(held&bit)==down) return;
        if(down) held|=bit; else held&=~bit;
        auto toggle=[&](Param p) { write(p,read(p)>.5f?0.f:1.f); };
        auto isHeld=[&](Button b) { return bool(held&(uint64_t{1}<<static_cast<unsigned>(b))); };
        if(button==Button::NudgeMinus||button==Button::NudgePlus) {
            if(isHeld(Button::Tap)) {
                if(down) { write(Param::AutoTempo,0); write(Param::Tempo,read(Param::Tempo)+(button==Button::NudgeMinus?-1:1)*(isHeld(Button::Auto)?.1f:1.f)); tapUsed=true; }
                send(Event{EventType::NudgeStop});
            } else {
                const int direction=isHeld(Button::NudgePlus)?1:isHeld(Button::NudgeMinus)?-1:0;
                send(Event{direction?EventType::NudgeStart:EventType::NudgeStop,0,static_cast<float>(direction)});
            }
            return;
        }
        if(button==Button::Bank||button==Button::Overdub||button==Button::Hold||button==Button::Tap) {
            bool& used=button==Button::Bank?bankUsed:button==Button::Overdub?deleteUsed:button==Button::Hold?muteUsed:tapUsed;
            if(down) {
                used=false;
                if(button==Button::Tap&&(isHeld(Button::NudgeMinus)||isHeld(Button::NudgePlus))) { used=true; send(Event{EventType::NudgeStop}); }
                return;
            }
            if(!used) {
                if(button==Button::Overdub) toggle(Param::Overdub);
                if(button==Button::Hold) { toggle(Param::XHold); if(read(Param::XHold)<.5f) send(Event{EventType::RollStop}); }
                if(button==Button::Tap) send(Event{EventType::Tap});
            }
            return;
        }
        if(!down) return;
        const int pad=static_cast<int>(button)-static_cast<int>(Button::Kick);
        if(pad>=0&&pad<4) {
            if(isHeld(Button::Bank)) {
                bankUsed=true;write(Param::XSource,0);
                if(read(Param::SampleSource)>.5f&&read(Param::Bank)==pad) {
                    selectedPad=pad;write(Param::SampleSource,0);send(Event{EventType::Trigger,static_cast<uint8_t>(pad)});
                } else {write(Param::Bank,static_cast<float>(pad));write(Param::SampleSource,1);}
            }
            else if(isHeld(Button::Overdub)&&read(Param::Overdub)>.5f) { deleteUsed=true; send(Event{EventType::DeletePad,static_cast<uint8_t>(pad)}); }
            else if(isHeld(Button::Hold)) {
                muteUsed=true;
                if(read(Param::Overdub)>.5f)send(Event{EventType::MutePad,static_cast<uint8_t>(pad)});
                else {selectedPad=pad;write(Param::XSource,0);send(Event{EventType::SelectPad,static_cast<uint8_t>(pad)});}
            }
            else { selectedPad=pad; write(Param::XSource,0); send(Event{EventType::Trigger,static_cast<uint8_t>(pad)}); }
            return;
        }
        const int scene=static_cast<int>(button)-static_cast<int>(Button::BpfEcho);
        if(scene>=0&&scene<10) { const bool same=read(Param::SceneType)==scene&&read(Param::SceneOn)>.5f; write(Param::SceneType,static_cast<float>(scene)); write(Param::SceneOn,same?0:1); return; }
        switch(button) {
            case Button::Quantize: toggle(Param::Quantize); break;
            case Button::Auto: if(isHeld(Button::Tap)) tapUsed=true; else toggle(Param::AutoTempo); break;
            case Button::Input: case Button::XPad: {
                const int source=static_cast<int>(read(Param::SceneSource));
                int bits=source==0?1:source==1?2:source==2?3:0;
                bits^=button==Button::Input?1:2;
                const float next=bits==0?3.f:bits==1?0.f:bits==2?1.f:2.f;
                write(Param::SceneSource,next); write(Param::IsolateSource,next); break;
            }
            case Button::Isolator: case Button::CutAdd: case Button::TransRoll: case Button::GateDrive:
                write(Param::IsolateMode,static_cast<float>(static_cast<int>(button)-static_cast<int>(Button::Isolator))); break;
            case Button::Roll: write(Param::XSource,1); break;
            default: break;
        }
    }
    template<class Send> void touch(bool down,Send send) noexcept {
        if(down==touchHeld) return;
        touchHeld=down;
        send(Event{down?EventType::RollStart:EventType::RollStop,static_cast<uint8_t>(selectedPad)});
    }
    int pad() const noexcept { return selectedPad; }
private:
    uint64_t held{};
    bool bankUsed{},deleteUsed{},muteUsed{},tapUsed{},touchHeld{};
    int selectedPad{};
};
}
