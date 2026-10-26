#include "rmx/FactoryEchoReturn.h"
#include "rmx/Wav.h"
#include <iostream>

int main(int argc,char** argv) {
    if(argc!=5) {
        std::cerr<<"Usage: rmx_spiral_return_probe PITCH_STREAM.wav NEW_RETURN.wav SUB1_RAW BPM\n"
                   "Component probe only: does not implement Spiral pitch generation.\n";
        return 1;
    }
    try {
        if(std::filesystem::exists(argv[2]))throw std::runtime_error("Output already exists");
        size_t used{};const std::string rawText=argv[3],bpmText=argv[4];
        const int raw=std::stoi(rawText,&used);
        if(used!=rawText.size()||raw<0||raw>255)throw std::runtime_error("Sub1 raw must be 0..255");
        const double bpm=std::stod(bpmText,&used);
        if(used!=bpmText.size()||!std::isfinite(bpm)||bpm<40||bpm>240)throw std::runtime_error("BPM must be 40..240");
        auto input=rmx::readWav(argv[1],180);
        if(input.rate!=48000)throw std::runtime_error("Component validation requires 48 kHz");
        rmx::FactoryEchoReturn processor;processor.prepare(48000);processor.restart(rmx::FactoryEchoReturn::Profile::spiral);
        rmx::Sample output;output.rate=48000;output.frames.resize(input.frames.size());
        for(size_t i=0;i<input.frames.size();++i) {
            const auto x=input.frames[i];const auto y=processor.process({x.l,x.r},raw,1,bpm);
            output.frames[i]={static_cast<float>(y[0]),static_cast<float>(y[1])};
        }
        rmx::writeWav(argv[2],output);
        std::cout<<"Rendered Spiral return component; no pitch generation or full-effect fidelity claim\n";
    } catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
