#include "rmx/Engine.h"
#include <chrono>
#include <iostream>
#include <numeric>
#include <cstdlib>

int main(int argc,char** argv) {
    const int blocks=argc>1?std::max(100,std::atoi(argv[1])):10000;
    auto bank=rmx::makeFactoryBank(); rmx::Engine engine; engine.setBank(&bank); engine.prepare(48000,128);
    engine.params.set(rmx::Param::SceneOn,1); engine.params.set(rmx::Param::SceneDepth,1);
    engine.params.set(rmx::Param::IsolateMode,3); engine.params.set(rmx::Param::Low,.8f); engine.params.set(rmx::Param::Mid,.8f); engine.params.set(rmx::Param::High,.8f);
    std::array<float,128> l{},r{},ol{},orr{}; for(size_t i=0;i<128;++i) l[i]=r[i]=std::sin(i*.13f)*.2f;
    double worst99=0;
    for(int mode=0;mode<4;++mode) for(int scene=0;scene<10;++scene) {
        engine.params.set(rmx::Param::IsolateMode,static_cast<float>(mode));
        engine.reset();
        engine.params.set(rmx::Param::SceneType,static_cast<float>(scene)); std::vector<double> timings; timings.reserve(static_cast<size_t>(blocks));
        for(int n=0;n<blocks+100;++n) {
            const float knob=n%500<250?.85f:-.85f;
            for(auto p:{rmx::Param::Low,rmx::Param::Mid,rmx::Param::High}) engine.params.set(p,knob);
            if(n%100==0) for(int pad=0;pad<4;++pad) engine.enqueue({rmx::EventType::Trigger,static_cast<uint8_t>(pad)});
            const auto start=std::chrono::steady_clock::now(); engine.process(l.data(),r.data(),ol.data(),orr.data(),128);
            const double us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-start).count(); if(n>=100) timings.push_back(us);
        }
        std::sort(timings.begin(),timings.end());
        const double p99=timings[static_cast<size_t>(blocks*.99)]/(128./48000*1e6)*100; worst99=std::max(worst99,p99);
        std::cout<<rmx::isolateNames[static_cast<size_t>(mode)]<<" / "<<rmx::sceneNames[static_cast<size_t>(scene)]<<": mean "<<std::accumulate(timings.begin(),timings.end(),0.)/blocks<<" us, p99 "<<p99<<"% deadline\n";
    }
    std::cout<<"Worst p99: "<<worst99<<"% (target < 50%)\n";
    return worst99<50?0:2;
}
