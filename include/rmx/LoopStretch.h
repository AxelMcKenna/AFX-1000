#pragma once
#include "Dsp.h"
#include <array>
#include <cstdint>
#include <limits>
#include <span>

namespace rmx {
// A bounded, stereo-linked overlap-add loop reader. The source timeline follows
// tempo; each overlapping reader follows pitch. Alignment reads the immutable
// sample directly, so voices need no audio buffers or callback allocations.
class LoopStretch {
public:
    void reset() noexcept { *this={}; }
    Stereo process(std::span<const Stereo> frames,double& timeline,double pitchStep,
                   double tempoStep,double outputRate,double sourceRate) noexcept {
        if(frames.empty())return {};
        if(!std::isfinite(timeline))timeline=0;
        outputRate=std::isfinite(outputRate)?outputRate:48000;
        sourceRate=std::isfinite(sourceRate)?std::clamp(sourceRate,8000.,192000.):48000;
        pitchStep=std::isfinite(pitchStep)?std::clamp(pitchStep,1./1024,1024.):1.;
        tempoStep=std::isfinite(tempoStep)?std::clamp(tempoStep,1./1024,1024.):1.;
        // Preserve the original samples and interpolation when no stretching is
        // required. Once a stretched voice is active, keep its readers running
        // across automation to avoid switching abruptly back to the timeline.
        if(!active&&std::abs(pitchStep-tempoStep)<1e-10) {
            const Stereo value=read(frames,timeline);
            timeline=wrap(timeline+tempoStep,frames.size());
            return value;
        }
        if(!active) {
            active=true;phase=0;
            hop=static_cast<uint32_t>(std::clamp(outputRate*.020,32.,3840.));
            previous=following=timeline;
        }
        const float t=static_cast<float>(phase)/hop;
        const float weight=t*t*(3-2*t); // Complementary smoothstep windows.
        const Stereo value=mix(read(frames,previous),read(frames,following),weight);
        previous=wrap(previous+pitchStep,frames.size());
        following=wrap(following+pitchStep,frames.size());
        timeline=wrap(timeline+tempoStep,frames.size());
        if(++phase==hop) {
            previous=following;
            following=align(frames,timeline,previous,pitchStep,sourceRate);
            phase=0;
        }
        return value;
    }
private:
    double previous{},following{};
    uint32_t phase{},hop{32};
    bool active{};
    static double wrap(double position,size_t length) noexcept {
        const double size=static_cast<double>(length);
        if(position>=size||position<0)position-=std::floor(position/size)*size;
        // Guard rounding at the boundary for very short loops.
        return position>=size?0:position;
    }
    static Stereo read(std::span<const Stereo> frames,double position) noexcept {
        position=wrap(position,frames.size());
        const auto first=static_cast<size_t>(position);
        const size_t next=first+1==frames.size()?0:first+1;
        return mix(frames[first],frames[next],static_cast<float>(position-first));
    }
    double align(std::span<const Stereo> frames,double desired,double reference,
                 double pitchStep,double sourceRate) const noexcept {
        if(frames.size()==1)return 0;
        // Search at most +/- 8 ms of source material, with a fixed upper bound
        // of 49 candidates and 24 stereo probes each. One shared offset keeps
        // stereo phase and polarity intact, including antiphase recordings.
        constexpr unsigned probes=24;
        std::array<Stereo,probes> target{};
        double targetEnergy=0;
        for(unsigned i=0;i<probes;++i) {
            target[i]=read(frames,reference+pitchStep*(hop-1)*i/(probes-1));
            targetEnergy+=target[i].l*target[i].l+target[i].r*target[i].r;
        }
        if(targetEnergy<1e-12)return desired;
        const double radius=std::max(1.,std::min(sourceRate*.008,frames.size()*.5));
        const double coarse=radius/16;
        double bestOffset=0,bestScore=-std::numeric_limits<double>::infinity();
        const auto inspect=[&](double offset) noexcept {
            if(std::abs(offset)>radius+1e-9)return;
            double dot=0,energy=0;
            for(unsigned i=0;i<probes;++i) {
                const Stereo candidate=read(frames,desired+offset+pitchStep*(hop-1)*i/(probes-1));
                dot+=target[i].l*candidate.l+target[i].r*candidate.r;
                energy+=candidate.l*candidate.l+candidate.r*candidate.r;
            }
            const double score=dot/std::sqrt(std::max(1e-24,targetEnergy*energy))-1e-6*std::abs(offset)/radius;
            if(score>bestScore) {bestScore=score;bestOffset=offset;}
        };
        inspect(0);
        for(int i=-16;i<=16;++i)if(i)inspect(i*coarse);
        double center=bestOffset;
        for(int i=-4;i<=4;++i)if(i)inspect(center+i*coarse/4);
        center=bestOffset;
        for(int i=-4;i<=4;++i)if(i)inspect(center+i*coarse/16);
        return wrap(desired+bestOffset,frames.size());
    }
};
static_assert(sizeof(LoopStretch)<=32,"Loop voices must retain a bounded embedded state");
}
