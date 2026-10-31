#include "rmx/Engine.h"
#include "rmx/Wav.h"
#include <fstream>
#include <iostream>

int main(int argc,char** argv){try{
    if(argc!=4||std::filesystem::exists(argv[2]))throw std::runtime_error("Usage: noise_user_probe SILENCE NEW_OUTPUT PLAN");
    const auto input=rmx::readWav(argv[1],2);if(input.rate!=48000)throw std::runtime_error("Requires48k");
    for(auto x:input.frames)if(x.l!=0||x.r!=0)throw std::runtime_error("Requires silent input");
    std::ifstream file(argv[3]);std::string magic,extra;unsigned version{},frames{},block{},user{},main{},amount{},width{},minimum{},maximum{};
    if(!(file>>magic>>version>>frames>>block>>user>>main>>amount>>width>>minimum>>maximum)||magic!="RMX_NOISE_USER"||version!=1
       ||frames<48000||frames>900*48000||block<8||block>4096||user>1||main>255||amount>255||width>2||minimum>3||maximum>3||file>>extra)
        throw std::runtime_error("Invalid Noise plan");
    rmx::Engine engine;engine.setOutputProtection(false);
    for(auto [p,value]:{std::pair{rmx::Param::AutoTempo,0.f},{rmx::Param::Quantize,0.f},{rmx::Param::SceneType,2.f},
        {rmx::Param::SceneSource,0.f},{rmx::Param::SceneOn,0.f},{rmx::Param::SceneDepth,main/255.f},
        {rmx::Param::SceneTime,amount*7.f/255},{rmx::Param::SceneResonance,0.f},{rmx::Param::UserSettings,static_cast<float>(user)},
        {rmx::Param::NoiseWidth,static_cast<float>(width)},{rmx::Param::NoiseMinimum,static_cast<float>(minimum)},{rmx::Param::NoiseMaximum,static_cast<float>(maximum)}})engine.params.set(p,value);
    engine.prepare(48000,block);rmx::Sample output;output.rate=48000;output.frames.resize(frames);
    std::array<float,4096> left{},right{};
    for(unsigned start=0;start<frames;){
        if(start==4800)engine.params.set(rmx::Param::SceneOn,1);
        unsigned count=std::min(block,frames-start);if(start<4800)count=std::min(count,4800-start);
        engine.process(nullptr,nullptr,left.data(),right.data(),count);
        for(unsigned i=0;i<count;++i)output.frames[start+i]={left[i],right[i]};start+=count;
    }
    rmx::writeWav(argv[2],output);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
