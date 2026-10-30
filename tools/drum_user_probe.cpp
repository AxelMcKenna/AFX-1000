#include "rmx/Engine.h"
#include "rmx/Wav.h"
#include <fstream>
#include <iostream>

int main(int argc,char** argv){try{
    if(argc!=5)throw std::runtime_error("Usage: drum_user_probe SILENCE NEW_OUTPUT SCHEDULE NEW_DRY");
    const auto output=std::filesystem::absolute(argv[2]).lexically_normal(),dryPath=std::filesystem::absolute(argv[4]).lexically_normal();
    if(output==dryPath||std::filesystem::exists(output)||std::filesystem::exists(dryPath))throw std::runtime_error("Outputs must be distinct and new");
    const auto input=rmx::readWav(argv[1],30);if(input.rate!=48000)throw std::runtime_error("User drum fixture requires48k");
    for(auto x:input.frames)if(x.l!=0||x.r!=0)throw std::runtime_error("User drum source must be silent");
    std::ifstream file(argv[3]);std::string magic;unsigned version{},pad{},level{},pitch{},block{},gain{},decay{},envelope{};
    if(!(file>>magic>>version>>pad>>level>>pitch>>block>>gain>>decay>>envelope)||magic!="RMX_DRUM_USER"||version!=1||pad>3||level>255||pitch>255||block<8||block>4096||gain>6||decay>2||envelope>1)
        throw std::runtime_error("Invalid User drum header");
    std::vector<size_t> hits;int64_t at{};
    while(file>>at){if(at<0||static_cast<size_t>(at)>=input.frames.size()||(!hits.empty()&&static_cast<size_t>(at)<hits.back()))throw std::runtime_error("Invalid User drum hit");hits.push_back(static_cast<size_t>(at));}
    if(!file.eof()||hits.empty())throw std::runtime_error("Invalid/empty User drum schedule");
    rmx::Engine engine;engine.setOutputProtection(false);
    engine.params.set(rmx::Param::AutoTempo,0);engine.params.set(rmx::Param::Quantize,0);engine.params.set(rmx::Param::Tempo,120);
    engine.params.set(rmx::Param::SampleSource,0);engine.params.set(rmx::Param::SceneOn,0);engine.params.set(rmx::Param::IsolateOn,0);engine.params.set(rmx::Param::UserSettings,1);
    engine.params.set(static_cast<rmx::Param>(static_cast<unsigned>(rmx::Param::KickGain)+pad),3.f-gain);
    engine.params.set(static_cast<rmx::Param>(static_cast<unsigned>(rmx::Param::KickDecay)+pad),decay);
    engine.params.set(static_cast<rmx::Param>(static_cast<unsigned>(rmx::Param::KickEnvelope)+pad),envelope);
    engine.params.set(rmx::Param::XLevel,level*1.5f/255);engine.params.set(rmx::Param::XPitch,pitch>=128?(pitch-128)*24.f/127:(static_cast<int>(pitch)-128)*24.f/128);
    engine.prepare(48000,block);
    rmx::Sample audio,dry;audio.rate=dry.rate=48000;audio.frames.resize(input.frames.size());dry.frames.resize(input.frames.size());
    std::array<float,4096> left{},right{};size_t event=0;
    for(size_t start=0;start<input.frames.size();){
        while(event<hits.size()&&hits[event]==start){engine.enqueue({rmx::EventType::Trigger,static_cast<uint8_t>(pad),1,0,0,0});++event;}
        size_t count=std::min<size_t>(block,input.frames.size()-start);if(event<hits.size())count=std::min(count,hits[event]-start);
        // The public original plan splits callbacks at both press and release.
        for(auto hit:hits)if(hit+32>start)count=std::min(count,hit+32-start);
        engine.process(nullptr,nullptr,left.data(),right.data(),static_cast<uint32_t>(count));
        for(size_t i=0;i<count;++i)audio.frames[start+i]={left[i],right[i]};start+=count;
    }
    rmx::writeWav(output,audio);rmx::writeWav(dryPath,dry);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
