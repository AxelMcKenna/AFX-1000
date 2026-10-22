#pragma once
#include <array>
#include <algorithm>
#include <cmath>
#include <limits>

namespace rmx {
// Four beats, relative to the first recorded hit. Events retain fractional beat
// positions; callback block size and the 24-PPQN MIDI clock do not limit timing.
class Sequencer {
public:
    struct Hit { unsigned pad{}, bank{}; float velocity{1};bool internal{},stop{}; };
    static constexpr double length=4;
    void clear() noexcept { steps={}; count=0; muted=0; origin=0; started=false; lastBeat=std::numeric_limits<double>::quiet_NaN(); due=infinity; }
    bool record(double beat,Hit hit) noexcept {
        if(!std::isfinite(beat)||!std::isfinite(hit.velocity)) return false;
        hit.pad%=4; hit.bank%=4; hit.velocity=std::clamp(hit.velocity,0.f,1.f);
        if(!started) { origin=beat; started=true; }
        const double position=wrap(beat-origin);
        // Repeated overdubs at the same musical position replace a hit instead
        // of growing an unbounded stack. One millisecond at 120 BPM is .002 beats.
        for(auto& step:steps) if(step.active&&step.hit.pad==hit.pad&&std::abs(step.position-position)<.002) {
            step.hit=hit; return true;
        }
        for(auto& step:steps) if(!step.active) {
            step={hit,position,beat+length,true}; ++count; due=std::min(due,step.next); return true;
        }
        return false;
    }
    void erase(unsigned pad) noexcept {
        for(auto& step:steps) if(step.active&&step.hit.pad==pad) { step.active=false; --count; }
        muted&=~(1u<<(pad%4)); updateDue();
    }
    void toggleMute(unsigned pad) noexcept { muted^=1u<<(pad%4); }
    unsigned muteMask() const noexcept { return muted; }
    size_t size() const noexcept { return count; }
    template<class Play> void advance(double beat,bool playing,Play play) noexcept {
        if(!started||!playing) return;
        // A host seek must not fire every missed event, or leave the sequence
        // waiting for its old absolute timeline after a backwards seek.
        if(std::isfinite(lastBeat)&&(beat<lastBeat-1e-7||beat-lastBeat>.25)) {
            for(auto& step:steps) if(step.active) {
                const double phase=wrap(beat-origin-step.position);
                step.next=beat+(phase<1e-7?0:length-phase);
            }
            updateDue();
        }
        lastBeat=beat;
        if(beat+1e-8<due) return;
        for(auto& step:steps) if(step.active&&step.next<=beat+1e-8) {
            if(!(muted&(1u<<step.hit.pad))) play(step.hit);
            step.next+=length*(1+std::floor(std::max(0.,beat-step.next)/length));
        }
        updateDue();
    }
private:
    static constexpr double infinity=std::numeric_limits<double>::infinity();
    struct Step { Hit hit{}; double position{},next{}; bool active{}; };
    std::array<Step,256> steps{};
    size_t count{}; unsigned muted{}; double origin{},due{infinity},lastBeat{infinity}; bool started{};
    static double wrap(double beat) noexcept { return beat-length*std::floor(beat/length); }
    void updateDue() noexcept { due=infinity; for(const auto& step:steps) if(step.active) due=std::min(due,step.next); }
};
}
