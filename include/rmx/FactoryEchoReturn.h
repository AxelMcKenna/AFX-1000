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
        age=0;readGain={};
    }
    // Constant-time transition: old delay contents are ignored until replaced.
    void restart(Profile next) noexcept {
        profile=next;age=0;readGain={};
        for(auto& channel:filters)for(auto& filter:channel) {
            filter.configure(next==Profile::crush?60:283.99944,rate);filter.reset();
        }
    }
    // The shared-clock path filters before the write gain and starts each
    // tap's read fade on its first complete block. Select filterInput once
    // after reset/restart; the default retains the established static API.
    std::array<double,2> process(const std::array<double,2>& feed,int timeRaw,float enabled,double bpm,float inputGain=1,bool filterInput=false) noexcept {
        timeRaw=std::clamp(timeRaw,0,255);
        auto source=feed;
        if(filterInput&&profile!=Profile::spiral){
            source={filters[0][1].tick(filters[0][0].tick(source[0])),filters[1][1].tick(filters[1][0].tick(source[1]))};
        }
        if(inputGain!=1)for(auto& value:source)value*=inputGain;
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
            auto tap=age>=static_cast<uint64_t>(delay)?lines[i].read(delay):Stereo{};
            if(filterInput){
                const auto firstRead=static_cast<uint64_t>(std::ceil(delay/32)*32);
                if(age>=firstRead)readGain[i]=std::min(1.f,readGain[i]+.00625f);
                tap=tap*readGain[i];
            }
            returned=returned+tap*weights[i];
            lines[i].push({static_cast<float>(std::clamp(source[0]*send*enabled+tap.l*.75,-8.,8.)),
                           static_cast<float>(std::clamp(source[1]*send*enabled+tap.r*.75,-8.,8.))});
        }
        ++age;
        if(profile==Profile::spiral||filterInput)return {returned.l*.7,returned.r*.7};
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
    std::array<float,4> readGain{};
    Profile profile{Profile::filter};double rate{48000};uint64_t age{};
};
}
