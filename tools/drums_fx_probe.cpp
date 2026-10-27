#include "rmx/Engine.h"
#include "rmx/Wav.h"
#include <fstream>
#include <iostream>
#ifdef RMX_DRUMS_SHARED_FIXTURE
#include "../research/audio/experiments/SharedDrumFX.h"
#endif

int main(int argc,char** argv){try{
    if(argc!=4)throw std::runtime_error("Usage: drums_fx_probe INPUT.wav NEW_OUTPUT.wav SCHEDULE.tsv");
    if(std::filesystem::exists(argv[2]))throw std::runtime_error("Output must be new");
    std::ifstream file(argv[3]);std::string magic;int version{},type{},source{},main{},amount{},cutoff{},enabled{},level{},pitch{};size_t block{};
    if(!(file>>magic>>version)||magic!="RMX_DRUM_FX"||version!=1
       ||!(file>>type>>source>>main>>amount>>cutoff>>enabled>>level>>pitch>>block)
       ||type<0||type>9||source<0||source>3||main<0||main>255||amount<0||amount>255||cutoff<0||cutoff>255
       ||enabled<0||enabled>1||level<0||level>255||pitch<0||pitch>255||block<8||block>4096)throw std::runtime_error("Invalid FX drum controls");
    const auto input=rmx::readWav(argv[1],60);if(input.rate!=48000)throw std::runtime_error("Requires 48 kHz");
    struct Button{size_t frame;unsigned pad;bool press;};std::vector<Button> events;int64_t at{};unsigned pad{};size_t previous=0;unsigned mask=0;
    while(file>>at){
        if(!(file>>pad)||at<0||static_cast<size_t>(at)+32>=input.frames.size()||pad>3||(!events.empty()&&static_cast<size_t>(at)<previous))throw std::runtime_error("Invalid drum event");
        if(events.empty()||static_cast<size_t>(at)!=previous)mask=0;
        if(mask&(1u<<pad))throw std::runtime_error("Duplicate simultaneous pad");mask|=1u<<pad;previous=static_cast<size_t>(at);
        events.push_back({previous,pad,true});events.push_back({previous+32,pad,false});
    }
    if(!file.eof()||events.empty())throw std::runtime_error("Invalid or empty hits");
    std::stable_sort(events.begin(),events.end(),[](const auto& a,const auto& b){return a.frame<b.frame;});
#ifdef RMX_DRUMS_SHARED_FIXTURE
    SharedDrumFX engine(type,source,main,amount,cutoff,enabled!=0,level,pitch);
#else
    rmx::Engine engine;engine.setOutputProtection(false);
    engine.params.set(rmx::Param::AutoTempo,0);engine.params.set(rmx::Param::Quantize,0);
    engine.params.set(rmx::Param::SceneType,static_cast<float>(type));engine.params.set(rmx::Param::SceneSource,static_cast<float>(source));
    engine.params.set(rmx::Param::SceneOn,static_cast<float>(enabled));engine.params.set(rmx::Param::SceneDepth,main/255.f);
    engine.params.set(rmx::Param::SceneTime,amount*7.f/255);engine.params.set(rmx::Param::SceneResonance,cutoff/255.f);
    engine.params.set(rmx::Param::XLevel,level*1.5f/255);engine.params.set(rmx::Param::XPitch,(pitch-128)*(pitch>=128?24.f/127:24.f/128));
    engine.prepare(48000,static_cast<uint32_t>(block));
#endif
    rmx::Sample output;output.rate=48000;output.frames.resize(input.frames.size());std::array<float,4096> left{},right{},ol{},orr{};size_t event=0;
    for(size_t start=0;start<output.frames.size();){
        while(event<events.size()&&events[event].frame==start){
            if(events[event].press){
#ifdef RMX_DRUMS_SHARED_FIXTURE
                engine.trigger(events[event].pad);
#else
                if(!engine.enqueue({rmx::EventType::Trigger,static_cast<uint8_t>(events[event].pad),1,0,0,0}))throw std::runtime_error("Event queue full");
#endif
            }++event;
        }
        size_t count=std::min(block,output.frames.size()-start);if(event<events.size())count=std::min(count,events[event].frame-start);
        for(size_t i=0;i<count;++i){left[i]=input.frames[start+i].l;right[i]=input.frames[start+i].r;}
#ifdef RMX_DRUMS_SHARED_FIXTURE
        std::array<rmx::Stereo,4096> in{},out{};for(size_t i=0;i<count;++i)in[i]={left[i],right[i]};
        engine.process(std::span<const rmx::Stereo>(in.data(),count),std::span<rmx::Stereo>(out.data(),count));
        for(size_t i=0;i<count;++i){ol[i]=out[i].l;orr[i]=out[i].r;}
#else
        engine.process(left.data(),right.data(),ol.data(),orr.data(),static_cast<uint32_t>(count));
#endif
        for(size_t i=0;i<count;++i)output.frames[start+i]={ol[i],orr[i]};start+=count;
    }
    rmx::writeWav(argv[2],output);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
