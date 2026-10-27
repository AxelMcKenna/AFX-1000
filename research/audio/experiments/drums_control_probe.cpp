#include "KickResearch.h"
#include "SnareResearch.h"
#include "ClapResearch.h"
#include "HatResearch.h"
#include "rmx/Wav.h"
#include <algorithm>
#include <fstream>
#include <iostream>
#include <variant>
int main(int argc,char** argv){try{
    if(argc!=5)throw std::runtime_error("Usage: drums_control_probe SILENCE NEW_OUTPUT SCHEDULE NEW_DRY");
    const auto outputPath=std::filesystem::absolute(argv[2]).lexically_normal(),dryPath=std::filesystem::absolute(argv[4]).lexically_normal();
    if(outputPath==dryPath||std::filesystem::exists(outputPath)||std::filesystem::exists(dryPath))throw std::runtime_error("Outputs must be distinct and new");
    auto input=rmx::readWav(argv[1],30);if(input.rate!=48000)throw std::runtime_error("Drum control research requires 48 kHz");
    for(auto x:input.frames)if(x.l!=0||x.r!=0)throw std::runtime_error("Drum source must be silent");
    std::ifstream file(argv[3]);std::string magic;int version{},drum{},level{},pitch{};size_t block{};
    if(!(file>>magic>>version>>drum>>level>>pitch>>block)||magic!="RMX_DRUM"||version!=1||drum<0||drum>3||level<0||level>255||pitch<0||pitch>255||block<8||block>4096)throw std::runtime_error("Invalid drum control schedule");
    std::vector<size_t> hits;int64_t frame{};while(file>>frame){if(frame<0||static_cast<size_t>(frame)+32>=input.frames.size()||(!hits.empty()&&static_cast<size_t>(frame)<=hits.back()+32))throw std::runtime_error("Invalid hit schedule");hits.push_back(static_cast<size_t>(frame));}
    if(!file.eof()||hits.empty())throw std::runtime_error("Invalid/empty hits");
    std::vector<std::pair<size_t,bool>> events;for(auto at:hits){events.push_back({at,true});events.push_back({at+32,false});}
    rmx::Sample output,dry;output.rate=dry.rate=48000;output.frames.resize(input.frames.size());dry.frames.resize(input.frames.size());
    std::variant<rmx::research::KickResearch,rmx::research::SnareResearch,rmx::research::ClapResearch,rmx::research::HatResearch> processor;
    switch(drum){case 0:processor.emplace<0>();break;case 1:processor.emplace<1>();break;case 2:processor.emplace<2>();break;case 3:processor.emplace<3>();break;}
    std::visit([&](auto& p){p.setControls(static_cast<unsigned>(level),static_cast<unsigned>(pitch));},processor);
    std::array<float,4096> audio{};size_t event=0;
    for(size_t start=0;start<input.frames.size();){
        while(event<events.size()&&events[event].first==start){if(events[event].second)std::visit([](auto& p){p.trigger();},processor);++event;}
        size_t n=std::min(block,input.frames.size()-start);if(event<events.size())n=std::min(n,events[event].first-start);
        std::visit([&](auto& p){p.process(std::span<float>(audio.data(),n));},processor);
        for(size_t i=0;i<n;++i)output.frames[start+i]={audio[i],audio[i]};start+=n;
    }
    rmx::writeWav(outputPath,output);rmx::writeWav(dryPath,dry);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
