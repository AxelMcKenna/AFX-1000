#pragma once
#include "Dsp.h"
#include <array>
#include <cstdint>

namespace rmx {
// Identified factory return component, validated at 48 kHz. A Spiral profile
// accepts the separately generated pitch stream; it is not a pitch model.
class FactoryEchoReturn {
public:
    enum class Profile { filter,crush,spiral };
    void prepare(double sampleRate) {
        rate=sampleRate;
        for(auto& line:lines)line.prepare(static_cast<size_t>(rate*1.5)+4);
        restart(Profile::filter);reset();
    }
    void reset() noexcept {
        for(auto& line:lines)line.reset();
        for(auto& channel:filters)for(auto& filter:channel)filter.reset();
        age=0;
    }
    // Constant-time transition: old delay contents are ignored until replaced.
    void restart(Profile next) noexcept {
        profile=next;age=0;
        for(auto& channel:filters)for(auto& filter:channel) {
            filter.configure(next==Profile::crush?60:283.99944,rate);filter.reset();
        }
    }
    std::array<double,2> process(const std::array<double,2>& feed,int timeRaw,float enabled,double bpm) noexcept {
        timeRaw=std::clamp(timeRaw,0,255);
        std::array<float,4> weights{};
        const float position=std::clamp((timeRaw-3)/62.25f,0.f,4.f);
        const unsigned upper=std::min(3u,static_cast<unsigned>(position));
        if(upper>0)weights[upper-1]=upper+1-position;
        weights[upper]=position-upper;
        if(position==4)weights[3]=1;
        const double beat=rate*std::floor(60000/std::clamp(bpm,40.,240.))/1000;
        const double send=profile==Profile::spiral?0.7079457843841379:1;
        Stereo returned{};
        for(size_t i=0;i<lines.size();++i) {
            const double delay=beat*(i+1)*.25;
            const auto tap=age>=static_cast<uint64_t>(delay)?lines[i].read(delay):Stereo{};
            returned=returned+tap*weights[i];
            lines[i].push({static_cast<float>(std::clamp(feed[0]*send*enabled+tap.l*.75,-8.,8.)),
                           static_cast<float>(std::clamp(feed[1]*send*enabled+tap.r*.75,-8.,8.))});
        }
        ++age;
        if(profile==Profile::spiral)return {returned.l*.7,returned.r*.7};
        return {filters[0][1].tick(filters[0][0].tick(returned.l))*.7,
                filters[1][1].tick(filters[1][0].tick(returned.r))*.7};
    }
private:
    struct HighPass {
        double b0{},b1{},b2{},a1{},a2{},s1{},s2{};
        void configure(double hz,double rate) noexcept {
            const double w=2*std::numbers::pi*hz/rate,alpha=std::sin(w)/std::sqrt(2.);
            a1=-2*std::cos(w)/(1+alpha);a2=(1-alpha)/(1+alpha);
            b0=(1-a1+a2)/4;b1=-2*b0;b2=b0;
        }
        double tick(double input) noexcept {
            const double output=b0*input+s1;s1=b1*input-a1*output+s2;s2=b2*input-a2*output;return output;
        }
        void reset() noexcept {s1=s2=0;}
    };
    std::array<FractionalDelay,4> lines;
    std::array<std::array<HighPass,2>,2> filters;
    Profile profile{Profile::filter};double rate{48000};uint64_t age{};
};
}
