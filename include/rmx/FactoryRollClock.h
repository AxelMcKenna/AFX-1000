#pragma once
#include <algorithm>
#include <cmath>

namespace rmx {
// Measured factory roll timing at48k. The96-beat phase offset
// and double rounding affect which generated32-frame block gets a repeat.
class FactoryRollClock {
public:
    void reset() noexcept {*this={};}
    void select(unsigned value) noexcept {pad=value%4;selected=true;}
    void beginCallback(bool synchronized,double beat,unsigned frames) noexcept {
        external=synchronized;
        if(!external){correction=lastHostBeat=0;return;}
        const double candidate=(32*(beat-lastHostBeat))/frames;lastHostBeat=beat;
        if(candidate>=0&&candidate<.0222)hostIncrement=candidate;
        // Finish a pending backward correction before accepting another.
        if(correction==0)correction=timeline-beat;
    }
    // A changed strip division rebases the offset but retains the new
    // division's previous phase under the old offset. Resetting both loses
    // the reference's occasional boundary retrigger. Equal writes only arm.
    void setDivision(double value) noexcept {
        if(value==division)return;
        division=value;
        previous=std::fmod(std::fmod(timeline,96.)+offset,division);
        offset=96-std::fmod(timeline,96.);
    }
    bool position() noexcept {
        positionReady=true;
        return heldTouch&&!running&&arm(pad,division);
    }
    void setQuantize(bool value) noexcept {quantized=value;}
    // Engaging Hold without an active touch freezes the inactive assignment.
    // A subsequent position write can explicitly rearm it.
    void setHold(bool value) noexcept {
        held=value;
        if(value){if(!physicalTouch){positionReady=running=false;}heldTouch=true;}
        else if(!physicalTouch)stop();
    }
    bool start(unsigned value,double beatDivision) noexcept {
        physicalTouch=heldTouch=true;
        return arm(value,beatDivision);
    }
    void release() noexcept {physicalTouch=false;if(!held)stop();}
    void stop(bool clearSelection=false) noexcept {running=positionReady=heldTouch=physicalTouch=false;if(clearSelection)selected=false;}
    bool selectOnly() const noexcept {return held&&running&&positionReady;}
    bool advance(double bpm) noexcept {
        const double scaled=32*bpm;
        const double increment=external?hostIncrement:scaled/(48000.*60);
        double adjustment=0;
        if(external){
            if(correction>0){adjustment=-std::min(correction,increment);correction=std::max(0.,correction-increment);}
            else{adjustment=-correction;correction=0;}
        }
        // A frozen Auto tick preserves the phase preceding a newly armed roll.
        if(adjustment==-increment){if(armed){previous=armPrevious;armed=false;}return false;}
        armed=false;
        timeline=(timeline+increment)+adjustment;
        const double phase=std::fmod(std::fmod(timeline,96.)+offset,division);
        const bool wrapped=phase<previous;previous=phase;return wrapped&&running&&selected;
    }
    double currentBeat() const noexcept {return timeline;}
    unsigned instrument() const noexcept {return pad;}
    bool active() const noexcept {return running&&selected;}
private:
    bool arm(unsigned value,double beatDivision) noexcept {
        if(!positionReady)return false;
        if(selected)pad=value%4;
        division=beatDivision;running=true;armPrevious=previous;armed=external;
        const double phase=std::fmod(timeline,96.);offset=96-phase;
        const double fraction=std::fmod(phase,.25);
        if(quantized){if(fraction<=.0325)offset+=fraction;else offset-=.25-fraction;}
        previous=std::fmod(std::fmod(timeline,96.)+offset,division);
        return selected&&(!quantized||fraction<=.0325);
    }
    double timeline{},offset{96},previous{},division{1},armPrevious{};
    double lastHostBeat{},hostIncrement{},correction{};
    unsigned pad{};bool running{},selected{},positionReady{true},quantized{},heldTouch{},physicalTouch{},held{},external{},armed{};
};
}
