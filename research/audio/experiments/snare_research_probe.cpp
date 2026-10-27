#include "rmx/drums/Snare.h"
#include "rmx/Wav.h"
#include <algorithm>
#include <fstream>
#include <iostream>
int main(int argc,char** argv){try{
    if(argc!=5)throw std::runtime_error("Usage: snare_research_probe SILENCE NEW_OUTPUT SCHEDULE NEW_DRY");
    if(std::filesystem::exists(argv[2])||std::filesystem::exists(argv[4]))throw std::runtime_error("Outputs must be new");
    auto input=rmx::readWav(argv[1],30);if(input.rate!=48000)throw std::runtime_error("Snare research requires 48 kHz");
    for(auto x:input.frames)if(x.l!=0||x.r!=0)throw std::runtime_error("Snare source must be silent");
    std::ifstream file(argv[3]);std::string magic;int version{},drum{},level{},pitch{};size_t block{};
    if(!(file>>magic>>version>>drum>>level>>pitch>>block)||magic!="RMX_DRUM"||version!=1||drum!=1||level!=128||pitch!=128||block<8||block>4096)throw std::runtime_error("Snare hypothesis only supports neutral raw128 controls");
    std::vector<size_t> hits;int64_t frame{};while(file>>frame){if(frame<0||static_cast<size_t>(frame)+32>=input.frames.size()||(!hits.empty()&&static_cast<size_t>(frame)<=hits.back()+32))throw std::runtime_error("Invalid hit schedule");hits.push_back(static_cast<size_t>(frame));}
    if(!file.eof()||hits.empty())throw std::runtime_error("Invalid/empty hits");
    std::vector<std::pair<size_t,bool>> events;for(auto at:hits){events.push_back({at,true});events.push_back({at+32,false});}
    rmx::Sample output,dry;output.rate=dry.rate=48000;output.frames.resize(input.frames.size());dry.frames.resize(input.frames.size());
    rmx::drums::Snare processor;std::array<float,4096> audio{};size_t event=0;
    for(size_t start=0;start<input.frames.size();){
        while(event<events.size()&&events[event].first==start){if(events[event].second)processor.trigger();++event;}
        size_t n=std::min(block,input.frames.size()-start);if(event<events.size())n=std::min(n,events[event].first-start);
        processor.process(std::span<float>(audio.data(),n));for(size_t i=0;i<n;++i)output.frames[start+i]={audio[i],audio[i]};start+=n;
    }
    rmx::writeWav(argv[2],output);rmx::writeWav(argv[4],dry);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
