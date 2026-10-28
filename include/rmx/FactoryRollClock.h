#pragma once
#include <cmath>

namespace rmx {
// Measured factory/unquantized roll timing at48k. The96-beat phase offset
// and double rounding affect which generated32-frame block gets a repeat.
class FactoryRollClock {
public:
    void reset() noexcept {*this={};}
    void select(unsigned value) noexcept {pad=value%4;selected=true;}
    bool start(unsigned value,double beatDivision) noexcept {
        if(!selected)return false;
        pad=value%4;division=beatDivision;running=true;
        offset=96-std::fmod(timeline,96.);
        previous=std::fmod(std::fmod(timeline,96.)+offset,division);
        return true;
    }
    void stop() noexcept {running=selected=false;}
    bool advance(double bpm) noexcept {
        const double scaled=32*bpm;
        const double increment=scaled/(48000.*60);
        timeline=timeline+increment;
        if(!running)return false;
        const double phase=std::fmod(std::fmod(timeline,96.)+offset,division);
        const bool wrapped=phase<previous;previous=phase;return wrapped;
    }
    unsigned instrument() const noexcept {return pad;}
    bool active() const noexcept {return running;}
private:
    double timeline{},offset{96},previous{},division{1};
    unsigned pad{};bool running{},selected{};
};
}
