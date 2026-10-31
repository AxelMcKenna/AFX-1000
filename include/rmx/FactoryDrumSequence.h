#pragma once
#include <array>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include "Parameters.h"

namespace rmx {
// Four-beat factory drum pattern:128 musical slots, advanced by the shared
// 32-frame clock. Record commands, rather than resampling generated audio.
class FactoryDrumSequence {
public:
    void clear() noexcept {*this={};}
    void clearPattern() noexcept {const bool active=enabled;clear();enabled=active;}
    void enable(bool value) noexcept {if(enabled!=value){const auto previousMute=muted;clear();enabled=value;if(!value)muted=previousMute;}}
    void quantize(bool value) noexcept {quantized=value;}
    void strip(unsigned division,bool touch) noexcept {
        if(!enabled)return;
        if(touch&&!writing)stripEdge=true;
        writing=touch;writeDivision=static_cast<uint8_t>(division);
    }
    void stripDivision(unsigned division) noexcept {writeDivision=static_cast<uint8_t>(division);}
    bool stripTouched() const noexcept {return writing;}
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
    void erase(uint8_t mask) noexcept {for(auto& slot:slots)slot&=static_cast<uint8_t>(~mask);muted&=static_cast<uint8_t>(~mask);rollPads&=static_cast<uint8_t>(~mask);}
    unsigned muteMask() const noexcept {return muted;}
    unsigned size() const noexcept {unsigned n=0;for(auto slot:slots)for(unsigned p=0;p<4;++p)n+=(slot>>p)&1u;return n;}
    template<class Play> void advance(double beat,bool playing,Play play) noexcept {
        if(!enabled||!started||!playing)return;
        const double phase=std::fmod(std::fmod(beat,96.)+offset,4.);
        const double fraction=std::fmod(phase,.03125);
        const bool boundary=fraction<previous;previous=fraction;
        // Strip motion occupies command slots continuously while touched.
        // Its write cursor leads the reader by one grid cell; unlike pad
        // one-shots, it never rounds to the nearest cell.
        const unsigned writeRegion=(quantized?static_cast<unsigned>(phase*4+.5)*8:static_cast<unsigned>(phase*32+.5))%128;
        if(writeRegion!=previousWriteRegion){stripWritten=false;previousWriteRegion=writeRegion;}
        if(writing&&!stripWritten){
            const unsigned index=(quantized?static_cast<unsigned>(phase*4+1)*8:static_cast<unsigned>(phase*32+1))%128;
            auto& command=stripSlots[index];
            command.division=writeDivision;command.present=true;
            command.edge=command.edge||stripEdge;stripEdge=false;
            if(quantized)for(unsigned i=1;i<8;++i){auto& following=stripSlots[(index+i)%128];following.division=writeDivision;following.present=true;}
            stripWritten=true;
        }
        if(pending){
            const unsigned index=quantized?static_cast<unsigned>(phase*4+.5)*8:static_cast<unsigned>(phase*32+.5);
            const unsigned slot=index<128?index:0;slots[slot]|=pending;
            if(index>=128||slot/32.>phase)skip[slot]|=pending;
            for(unsigned pad=0;pad<4;++pad)if(pending&(1u<<pad))velocity[slot][pad]=pendingVelocity[pad];
        }
        uint8_t played=0;
        if(boundary){
            const unsigned slot=static_cast<unsigned>(phase*32+.5)%128;
            const auto mask=static_cast<uint8_t>(slots[slot]&~pending&~skip[slot]);
            skip[slot]=0;
            for(unsigned pad=0;pad<4;++pad)if(mask&(1u<<pad))play(pad,velocity[slot][pad]);
            played=mask;
            if(stripSlots[slot].edge){
                rollPads=lastPads(static_cast<unsigned>(phase*32)%128);
                rebase(rollPads,phase);
            }
        }
        const auto& command=stripSlots[static_cast<unsigned>(phase*32)%128];
        if(command.present){
            rebase(static_cast<uint8_t>(pending|played),phase);
            const double division=xPadBeatValues[command.division];
            const double now=std::fmod(phase,division),before=std::fmod(previousPosition,division);
            for(unsigned pad=0;pad<4;++pad)if(rollPads&(1u<<pad)){
                const auto positive=[division](double value){const double result=std::fmod(value,division);return result<0?result+division:result;};
                if(positive(now-rollOffsets[pad])<positive(before-rollOffsets[pad]))play(pad,1);
            }
        }else rollPads=0;
        previousPosition=phase;
        pending=0;
    }
private:
    uint8_t lastPads(unsigned slot) const noexcept {
        for(unsigned i=0;i<128;++i)if(const auto mask=slots[(slot+128-i)%128])return mask;
        return 0;
    }
    void rebase(uint8_t mask,double phase) noexcept {
        const double grid=quantized?.25:.03125;
        for(unsigned pad=0;pad<4;++pad)if(mask&(1u<<pad)){rollPads|=static_cast<uint8_t>(1u<<pad);rollOffsets[pad]=static_cast<int>(phase/grid+.5)*grid;}
    }
    struct StripCommand {uint8_t division{};bool present{},edge{};};
    std::array<StripCommand,128> stripSlots{};
    std::array<double,4> rollOffsets{};
    std::array<uint8_t,128> slots{},skip{};
    std::array<std::array<float,4>,128> velocity{};
    std::array<float,4> pendingVelocity{};
    double offset{},previous{},previousPosition{};
    unsigned previousWriteRegion{};
    uint8_t pending{},muted{},writeDivision{},rollPads{};bool enabled{},started{},quantized{},writing{},stripEdge{},stripWritten{};
};
}
