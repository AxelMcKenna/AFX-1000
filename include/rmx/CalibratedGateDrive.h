#pragma once
#include "rmx/Dsp.h"
#include <array>
#include <span>

namespace rmx {
// Default 48 kHz Gate/Drive on the common 32-sample clock. See research/audio/isolate-modes.md.
class CalibratedGateDrive {
public:
    void reset() noexcept;
    void setControls(std::array<unsigned,3> lowMidHigh,bool active) noexcept {
        for(size_t i=0;i<3;++i)controls[2-i]=std::min(lowMidHigh[i],255u);
        enabled=active;
    }
    void process(std::span<const Stereo,32> input,std::span<Stereo,32> output) noexcept;
private:
    struct Biquad {
        std::array<float,5> c{};std::array<float,4> state{};
        void process(std::span<const Stereo,32> input,std::span<Stereo,32> output) noexcept;
    };
    struct Fourth {
        Biquad first,second;
        void configure(std::array<float,5> c) noexcept;
        void process(std::span<const Stereo,32> input,std::span<Stereo,32> output) noexcept;
    };
    Fourth lpLow,hpLow,lpHigh,hpHigh;
    struct Level {
        std::array<float,24> history{};
        float peak{},held{.05f},smooth{.05f},step{},target{};
        unsigned count{},position{},wait{},ramp{};bool warming{true};
        Level() noexcept;
        void update(std::span<const Stereo,32> band) noexcept;
    };
    struct Band {
        Level level;
        Biquad lowExtra,post;
        int raw{128},side{-1};bool neutral{true};
        unsigned fade{};float dry{1},dryStep{},dryTarget{1};
        float mix{},mixStep{.00625f},inputGain{1},outputGain{1};
        float threshold{.05f},thresholdTarget{.05f},thresholdStep{};unsigned thresholdBlocks{};
        float envelope{},gate{1},gateOutput{1};
        void updateThreshold() noexcept;
        void finishThreshold() noexcept;
    };
    std::array<Band,3> bands{};
    std::array<unsigned,3> controls{128,128,128};
    float master{1},step{};unsigned phase{};bool selected{},enabled{},initializing{};
    void initializeBands() noexcept;
    void prepare() noexcept;
    void processBand(unsigned index,std::span<const Stereo,32> input,std::span<Stereo,32> output) noexcept;

};
}
