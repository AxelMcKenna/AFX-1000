#include "rmx/Engine.h"
#include "rmx/Wav.h"
#include <fstream>
#include <iostream>
#include <sstream>

int main(int argc,char** argv){try{
    if(argc!=5)throw std::runtime_error("Usage: drum_probe SILENCE.wav NEW_OUTPUT.wav SCHEDULE.tsv NEW_DRY.wav");
    if(std::filesystem::absolute(argv[2]).lexically_normal()==std::filesystem::absolute(argv[4]).lexically_normal()
       ||std::filesystem::exists(argv[2])||std::filesystem::exists(argv[4]))throw std::runtime_error("Outputs must be distinct and new");
    const auto input=rmx::readWav(argv[1],30);
    if(input.rate!=48000)throw std::runtime_error("Drum fixture requires 48 kHz");
    for(const auto x:input.frames)if(x.l!=0||x.r!=0)throw std::runtime_error("Drum fixture requires silent input");
    std::ifstream file(argv[3]);std::string magic;int version{},drum{},level{},pitch{};size_t block{};std::vector<std::pair<size_t,unsigned>> hits;
    if(!(file>>magic>>version)||magic!="RMX_DRUM"||(version!=1&&version!=2)||!(file>>drum>>level>>pitch>>block)
        ||drum<0||drum>3||level<0||level>255||pitch<0||pitch>255||block<8||block>4096)throw std::runtime_error("Invalid drum schedule");
    int64_t at{};unsigned padsAtFrame=0;while(file>>at){
        unsigned pad=static_cast<unsigned>(drum);if(version==2&&!(file>>pad))throw std::runtime_error("Missing drum pad");
        if(at<0||static_cast<size_t>(at)+32>=input.frames.size()||pad>3||(!hits.empty()&&static_cast<size_t>(at)<hits.back().first))throw std::runtime_error("Invalid hit extent/order");
        if(hits.empty()||static_cast<size_t>(at)!=hits.back().first)padsAtFrame=0;
        if(padsAtFrame&(1u<<pad))throw std::runtime_error("Duplicate simultaneous pad");padsAtFrame|=1u<<pad;
        hits.emplace_back(static_cast<size_t>(at),pad);
    }
    if(!file.eof()||hits.empty())throw std::runtime_error("Invalid or empty drum hits");
    auto bank=rmx::makeFactoryBank(48000,false);rmx::Engine engine;engine.setBank(&bank);engine.setOutputProtection(false);
    engine.params.set(rmx::Param::AutoTempo,0);engine.params.set(rmx::Param::Quantize,0);
    engine.params.set(rmx::Param::SampleSource,0);engine.params.set(rmx::Param::SceneType,1);
    engine.params.set(rmx::Param::SceneOn,0);engine.params.set(rmx::Param::IsolateOn,0);
    engine.params.set(rmx::Param::XLevel,level*1.5f/255);
    engine.params.set(rmx::Param::XPitch,pitch>=128?(pitch-128)*24.f/127:(pitch-128)*24.f/128);
    engine.prepare(48000,static_cast<uint32_t>(block));
    rmx::Sample output,dry;output.rate=dry.rate=48000;output.frames.resize(input.frames.size());dry.frames.resize(input.frames.size());
    struct Button{size_t frame;bool pressed;unsigned pad;};std::vector<Button> events;for(auto [at,pad]:hits){events.push_back({at,true,pad});events.push_back({at+32,false,pad});}
    std::stable_sort(events.begin(),events.end(),[](const auto& a,const auto& b){return a.frame<b.frame;});
    std::array<float,4096> left{},right{};size_t event=0;
    for(size_t start=0;start<output.frames.size();){
        while(event<events.size()&&events[event].frame==start){if(events[event].pressed)engine.enqueue({rmx::EventType::Trigger,static_cast<uint8_t>(events[event].pad),1,0,0,0});++event;}
        size_t count=std::min(block,output.frames.size()-start);
        if(event<events.size())count=std::min(count,events[event].frame-start);
        engine.process(nullptr,nullptr,left.data(),right.data(),static_cast<uint32_t>(count));
        for(size_t i=0;i<count;++i)output.frames[start+i]={left[i],right[i]};start+=count;
    }
    rmx::writeWav(argv[2],output);rmx::writeWav(argv[4],dry);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
