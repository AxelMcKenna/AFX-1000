#pragma once
#include "CalibratedReleaseEcho.h"
#include "CalibratedReleaseBrake.h"
#include "CalibratedReleaseSpin.h"

namespace rmx {
// The three default-profile48k Release processors share one work region and
// a continuously recorded reverse-history region. Allocation is prepare-only.
class FactoryRelease {
public:
    void prepare(){
        storage.assign(589824+196608,{});
        auto work=std::span<Stereo>{storage}.first(589824);
        auto raw=std::span<Stereo>{storage}.subspan(589824);
        echo.attach(work);brake.attach(work);spin.attach(raw,work.first(196608));reset();
    }
    // The legacy and measured Release processors never run together. Their
    // backing memory is shared, keeping full-bank replacement within SDRAM.
    std::span<Stereo> legacyStorage() noexcept {return std::span<Stereo>{storage}.first(48000*16+4);}
    void invalidate() noexcept {
        echo.resetState();brake.resetState();spin.resetState();spin.resetHistoryPosition();
        current=3;target=1;position=returnFrames=0;master=1;masterStep=0;masterPhase=0;
    }
    void reset() noexcept {std::fill(storage.begin(),storage.end(),Stereo{});invalidate();}
    void setControls(unsigned type,unsigned lever,bool enabled) noexcept {target=std::min(type,2u);const unsigned next=enabled?std::min(lever,255u):0;
        if(!next&&position)returnFrames=160;else if(next)returnFrames=0;
        position=next;}
    void process(std::span<const Stereo,32> input,std::span<Stereo,32> output,double bpm) noexcept;

private:
    std::pmr::vector<Stereo> storage;CalibratedReleaseEcho echo;CalibratedReleaseBrake brake;CalibratedReleaseSpin spin;
    unsigned current{3},target{1},position{},returnFrames{},masterPhase{};float master{1},masterStep{};
};
}
