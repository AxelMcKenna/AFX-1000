#pragma once
#include <array>
#include <algorithm>
#include <cmath>
#include <cstdint>

namespace rmx {
// Four-beat factory drum pattern:128 musical slots, advanced by the shared
// 32-frame clock. Record commands, rather than resampling generated audio.
class FactoryDrumSequence {
public:
    void clear() noexcept {*this={};}
    void clearPattern() noexcept {const bool active=enabled;clear();enabled=active;}
    void enable(bool value) noexcept {if(enabled!=value){clear();enabled=value;}}
    void quantize(bool value) noexcept {quantized=value;}
    void record(uint8_t mask,const std::array<float,4>& values,double beat) noexcept {
        if(!enabled||!mask)return;
        if(!started){
            const double phase=std::fmod(beat,96.);
            const double grid=quantized?.25:.03125,fraction=std::fmod(phase,grid);
            offset=96-phase;
            if(fraction<=grid*.5)offset+=fraction;else offset-=grid-fraction;
            previous=std::fmod(phase+offset,.03125);started=true;
        }
        pending|=mask;
        for(unsigned pad=0;pad<4;++pad)if(mask&(1u<<pad))pendingVelocity[pad]=values[pad];
    }
    void toggleMute(uint8_t mask) noexcept {muted^=mask;}
    void erase(uint8_t mask) noexcept {for(auto& slot:slots)slot&=static_cast<uint8_t>(~mask);muted&=static_cast<uint8_t>(~mask);}
    unsigned muteMask() const noexcept {return muted;}
    unsigned size() const noexcept {unsigned n=0;for(auto slot:slots)for(unsigned p=0;p<4;++p)n+=(slot>>p)&1u;return n;}
    template<class Play> void advance(double beat,bool playing,Play play) noexcept {
        if(!enabled||!started||!playing)return;
        const double phase=std::fmod(std::fmod(beat,96.)+offset,4.);
        const double fraction=std::fmod(phase,.03125);
        const bool boundary=fraction<previous;previous=fraction;
        if(pending){
            const unsigned index=quantized?static_cast<unsigned>(phase*4+.5)*8:static_cast<unsigned>(phase*32+.5);
            const unsigned slot=index<128?index:0;slots[slot]|=pending;
            if(index>=128||slot/32.>phase)skip[slot]|=pending;
            for(unsigned pad=0;pad<4;++pad)if(pending&(1u<<pad))velocity[slot][pad]=pendingVelocity[pad];
        }
        if(boundary){
            const unsigned slot=static_cast<unsigned>(phase*32+.5)%128;
            const auto mask=static_cast<uint8_t>(slots[slot]&~pending&~skip[slot]);
            skip[slot]=0;
            for(unsigned pad=0;pad<4;++pad)if(mask&(1u<<pad))play(pad,velocity[slot][pad]);
        }
        pending=0;
    }
private:
    std::array<uint8_t,128> slots{},skip{};
    std::array<std::array<float,4>,128> velocity{};
    std::array<float,4> pendingVelocity{};
    double offset{},previous{};
    uint8_t pending{},muted{};bool enabled{},started{},quantized{};
};
}
