#include "rmx/Engine.h"
#include "rmx/Wav.h"
#ifdef RMX_RELEASE_RESEARCH
#include "rmx/CalibratedReleaseEcho.h"
#include "rmx/CalibratedReleaseBrake.h"
#include "rmx/CalibratedReleaseSpin.h"
#endif
#include <fstream>
#include <iostream>
int main(int argc,char** argv){try{
    if(argc!=4)throw std::runtime_error("Usage: release_probe INPUT NEW_OUTPUT SCHEDULE");
    const auto path=std::filesystem::absolute(argv[2]).lexically_normal();if(std::filesystem::exists(path))throw std::runtime_error("Output must be new");
    const auto input=rmx::readWav(argv[1],30);if(input.rate!=48000)throw std::runtime_error("Requires48k");
    std::ifstream file(argv[3]);std::string magic;unsigned version{},type{},block{};double bpm{};
    if(!(file>>magic>>version>>type>>block>>bpm)||magic!="RMX_RELEASE"||version!=1||type>2||block<8||block>4096||!std::isfinite(bpm)||bpm<40||bpm>240)throw std::runtime_error("Invalid release schedule");
    struct Change{size_t frame;unsigned raw;};std::vector<Change> changes;int64_t frame{};unsigned raw{};
    while(file>>frame){if(!(file>>raw)||frame<0||static_cast<size_t>(frame)>=input.frames.size()||raw>255||(!changes.empty()&&static_cast<size_t>(frame)<changes.back().frame))throw std::runtime_error("Invalid release event");changes.push_back({static_cast<size_t>(frame),raw});}
    if(!file.eof())throw std::runtime_error("Malformed release schedule");
    rmx::Engine engine;engine.setOutputProtection(false);engine.params.set(rmx::Param::AutoTempo,0);engine.params.set(rmx::Param::Quantize,0);engine.params.set(rmx::Param::Tempo,static_cast<float>(bpm));engine.params.set(rmx::Param::SceneOn,0);engine.params.set(rmx::Param::IsolateOn,0);engine.params.set(rmx::Param::ReleaseType,static_cast<float>(type));engine.prepare(48000,block);
    rmx::Sample output;output.rate=48000;output.frames.resize(input.frames.size());std::array<float,4096> left{},right{},a{},b{};size_t event=0;
    for(size_t start=0;start<input.frames.size();){
        while(event<changes.size()&&changes[event].frame==start){
#ifdef RMX_RELEASE_RESEARCH
            if(false)
#endif
            engine.params.set(rmx::Param::ReleaseAmount,changes[event].raw/255.f);++event;}
        size_t count=std::min<size_t>(block,input.frames.size()-start);if(event<changes.size())count=std::min(count,changes[event].frame-start);
        for(size_t i=0;i<count;++i){left[i]=input.frames[start+i].l;right[i]=input.frames[start+i].r;}
        engine.process(left.data(),right.data(),a.data(),b.data(),static_cast<uint32_t>(count));for(size_t i=0;i<count;++i)output.frames[start+i]={a[i],b[i]};start+=count;
    }
#ifdef RMX_RELEASE_RESEARCH
    auto apply=[&](auto& processor){
        processor.prepare();size_t next=0;unsigned current=0;
        for(size_t start=32;start+32<=output.frames.size();start+=32){
            while(next<changes.size()&&(changes[next].frame/32+1)*32<=start){current=(changes[next].raw/85)*85;++next;}
            std::array<rmx::Stereo,32> result{};processor.process(std::span<const rmx::Stereo,32>{output.frames.data()+start,32},result,current,bpm);std::copy(result.begin(),result.end(),output.frames.begin()+static_cast<std::ptrdiff_t>(start));
        }
    };
    if(type==0){rmx::CalibratedReleaseSpin processor;apply(processor);}
    if(type==1){rmx::CalibratedReleaseEcho processor;apply(processor);}
    if(type==2){rmx::CalibratedReleaseBrake processor;apply(processor);}
#endif
    rmx::writeWav(path,output);
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
