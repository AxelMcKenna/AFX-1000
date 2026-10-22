#include "rmx/Engine.h"
#include "rmx/State.h"
#include "rmx/Wav.h"
#include <iostream>

int main(int argc,char** argv) {
    if(argc<3||argc>4) { std::cerr<<"Usage: rmx_render input.wav output.wav [preset.rmx]\n"; return 1; }
    try {
        auto input=rmx::readWav(argv[1],60*60); auto bank=rmx::makeFactoryBank(); rmx::Engine engine;
        if(argc==4) { auto state=rmx::State::load(argv[3]); state.apply(engine.params); for(size_t i=0;i<16;++i) if(!state.samplePaths[i].empty()) bank.slots[i]=rmx::readWav(state.samplePaths[i]); state.applySamples(bank); }
        engine.setBank(&bank); engine.prepare(input.rate,256);
        rmx::Sample output; output.rate=input.rate; output.frames.resize(input.frames.size()+static_cast<size_t>(input.rate*4));
        std::array<float,256> l{},r{},ol{},orr{};
        for(size_t start=0;start<output.frames.size();start+=256) {
            const auto n=static_cast<uint32_t>(std::min(size_t(256),output.frames.size()-start));
            for(size_t i=0;i<n;++i) { auto x=start+i<input.frames.size()?input.frames[start+i]:rmx::Stereo{}; l[i]=x.l; r[i]=x.r; }
            engine.process(l.data(),r.data(),ol.data(),orr.data(),n);
            for(size_t i=0;i<n;++i) output.frames[start+i]={ol[i],orr[i]};
        }
        rmx::writeWav(argv[2],output); std::cout<<"Rendered "<<output.frames.size()<<" stereo frames at "<<output.rate<<" Hz\n";
    } catch(const std::exception& e) { std::cerr<<e.what()<<'\n'; return 1; }
}
