#include "rmx/Engine.h"
#include "rmx/Wav.h"
#include <fstream>
#include <iostream>

int main(int argc,char** argv){try{
    if(argc!=5)throw std::runtime_error("Usage: drum_motion_probe SILENCE NEW_OUTPUT SCHEDULE NEW_DRY");
    const auto out=std::filesystem::absolute(argv[2]).lexically_normal(),dryPath=std::filesystem::absolute(argv[4]).lexically_normal();
    if(out==dryPath||std::filesystem::exists(out)||std::filesystem::exists(dryPath))throw std::runtime_error("Outputs must be distinct and new");
    const auto input=rmx::readWav(argv[1],30);
    if(input.rate!=48000)throw std::runtime_error("Drum motion fixture requires48k");
    for(auto x:input.frames)if(x.l!=0||x.r!=0)throw std::runtime_error("Drum motion source must be silent");
    std::ifstream file(argv[3]);std::string magic;unsigned version{},level{},pitch{},block{};
    if(!(file>>magic>>version>>level>>pitch>>block)||magic!="RMX_DRUM_MOTION"||version!=1||level>255||pitch>255||block<8||block>4096)
        throw std::runtime_error("Invalid drum motion header");
    struct Change{size_t frame;char type;unsigned value;};std::vector<Change> events;
    int64_t at{};char type{};unsigned value{};
    while(file>>at){
        if(!(file>>type>>value)||at<0||static_cast<size_t>(at)>=input.frames.size()||(!events.empty()&&static_cast<size_t>(at)<events.back().frame)
           ||(type!='H'&&type!='R'&&type!='L'&&type!='P')||value>((type=='H'||type=='R')?3u:255u))throw std::runtime_error("Invalid drum motion event");
        events.push_back({static_cast<size_t>(at),type,value});
    }
    if(!file.eof()||events.empty())throw std::runtime_error("Invalid/empty drum motion schedule");
    rmx::Engine engine;engine.setOutputProtection(false);
    engine.params.set(rmx::Param::AutoTempo,0);engine.params.set(rmx::Param::Quantize,0);
    engine.params.set(rmx::Param::SampleSource,0);engine.params.set(rmx::Param::SceneOn,0);engine.params.set(rmx::Param::IsolateOn,0);
    auto setLevel=[&](unsigned raw){engine.params.set(rmx::Param::XLevel,raw*1.5f/255);};
    auto setPitch=[&](unsigned raw){engine.params.set(rmx::Param::XPitch,raw>=128?(raw-128)*24.f/127:(static_cast<int>(raw)-128)*24.f/128);};
    setLevel(level);setPitch(pitch);engine.prepare(48000,block);
    rmx::Sample audio,dry;audio.rate=dry.rate=48000;audio.frames.resize(input.frames.size());dry.frames.resize(input.frames.size());
    std::array<float,4096> left{},right{};size_t event=0;
    for(size_t start=0;start<input.frames.size();){
        while(event<events.size()&&events[event].frame==start){
            const auto e=events[event++];
            if(e.type=='H')engine.enqueue({rmx::EventType::Trigger,static_cast<uint8_t>(e.value),1,0,0,0});
            else if(e.type=='L')setLevel(e.value);
            else if(e.type=='P')setPitch(e.value);
            // Button releases split host callbacks but do not stop a drum.
        }
        size_t count=std::min<size_t>(block,input.frames.size()-start);
        if(event<events.size())count=std::min(count,events[event].frame-start);
        engine.process(nullptr,nullptr,left.data(),right.data(),static_cast<uint32_t>(count));
        for(size_t i=0;i<count;++i)audio.frames[start+i]={left[i],right[i]};start+=count;
    }
    rmx::writeWav(out,audio);rmx::writeWav(dryPath,dry);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
