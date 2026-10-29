#include "rmx/Engine.h"
#include "rmx/Wav.h"
#ifdef RMX_ISOLATE_RESEARCH
#include "../research/audio/experiments/IsolateNeutral.h"
#endif
#include <fstream>
#include <cstdlib>
#include <iomanip>
#include <iostream>
int main(int argc,char** argv){try{
    if(argc!=4)throw std::runtime_error("Usage: isolate_modes_probe INPUT NEW_OUTPUT SCHEDULE");
    const auto output=std::filesystem::absolute(argv[2]).lexically_normal();
    if(std::filesystem::exists(output))throw std::runtime_error("Output must be new");
    const auto source=rmx::readWav(argv[1],30);if(source.rate!=48000)throw std::runtime_error("Requires 48 kHz");
    std::ifstream file(argv[3]);std::string magic;unsigned version{},mode{},block{};double bpm{};
    if(!(file>>magic>>version>>mode>>block>>bpm)||magic!="RMX_ISOLATE_MODES"||(version!=1&&version!=2)||mode>3||block<8||block>4096||!std::isfinite(bpm)||bpm<40||bpm>240)throw std::runtime_error("Invalid Isolate schedule");
    struct Change{size_t frame;unsigned band,raw;};std::vector<Change> changes;int64_t frame{};unsigned band{},raw{};
    while(file>>frame){if(!(file>>band>>raw)||frame<0||static_cast<size_t>(frame)>=source.frames.size()||band>(version==1?2u:3u)||raw>255||(band==3&&raw>1)||(!changes.empty()&&static_cast<size_t>(frame)<changes.back().frame))throw std::runtime_error("Invalid Isolate event");changes.push_back({static_cast<size_t>(frame),band,raw});}
    if(!file.eof())throw std::runtime_error("Malformed Isolate schedule");
    rmx::Engine engine;engine.setOutputProtection(false);
    engine.params.set(rmx::Param::AutoTempo,0);engine.params.set(rmx::Param::Quantize,0);engine.params.set(rmx::Param::Tempo,static_cast<float>(bpm));
    engine.params.set(rmx::Param::SceneOn,0);engine.params.set(rmx::Param::SceneSource,0);engine.params.set(rmx::Param::IsolateSource,0);
    engine.params.set(rmx::Param::IsolateOn,1);engine.params.set(rmx::Param::IsolateMode,static_cast<float>(mode));
    constexpr std::array<rmx::Param,3> bands{rmx::Param::Low,rmx::Param::Mid,rmx::Param::High};
    for(auto p:bands)engine.params.set(p,(128/255.f)*2-1);
#ifdef RMX_ISOLATE_RESEARCH
    if(mode==2||mode==3)engine.params.set(rmx::Param::IsolateOn,0);
#endif
    engine.prepare(48000,block);std::array<float,4096> left{},right{},a{},b{};rmx::Sample result;result.rate=48000;result.frames.resize(source.frames.size());size_t next=0;
    for(size_t start=0;start<source.frames.size();){
        while(next<changes.size()&&changes[next].frame==start){if(changes[next].band<3)engine.params.set(bands[changes[next].band],(changes[next].raw/255.f)*2-1);else engine.params.set(rmx::Param::IsolateOn,static_cast<float>(changes[next].raw));++next;}
        size_t count=std::min<size_t>(block,source.frames.size()-start);if(next<changes.size())count=std::min(count,changes[next].frame-start);
        for(size_t i=0;i<count;++i){left[i]=source.frames[start+i].l;right[i]=source.frames[start+i].r;}
        engine.process(left.data(),right.data(),a.data(),b.data(),static_cast<uint32_t>(count));for(size_t i=0;i<count;++i)result.frames[start+i]={a[i],b[i]};start+=count;
    }
#ifdef RMX_ISOLATE_RESEARCH
    if(mode==2||mode==3){
        rmx::research::IsolateNeutral processor;processor.mode=mode;processor.prepare();size_t requested=0;
        std::ofstream trace;if(auto name=std::getenv("RMX_ISOLATE_NATIVE_TRACE")){if(std::filesystem::exists(name))throw std::runtime_error("Trace must be new");trace.open(name);trace<<std::setprecision(10);}
        // The shared transport leaves unfilled startup slots in their host
        // callback positions. Process the input clock before transporting it;
        // filtering a completed dry render loses the first block's history.
        std::array<rmx::Stereo,32> collected{},pending{};size_t received=0,available=0,head=0,age=0;float fade=0;
        result.frames=source.frames;size_t change=0;
        for(size_t start=0;start<result.frames.size();){
            while(change<changes.size()&&changes[change].frame==start)++change;
            size_t count=std::min<size_t>(block,result.frames.size()-start);if(change<changes.size())count=std::min(count,changes[change].frame-start);
            size_t read=0,written=0;
            while(read<count){
                const auto take=std::min(32-received,count-read);std::copy_n(source.frames.begin()+static_cast<std::ptrdiff_t>(start+read),take,collected.begin()+static_cast<std::ptrdiff_t>(received));received+=take;read+=take;
                const auto emit=std::min(available,count-written);std::copy_n(pending.begin()+static_cast<std::ptrdiff_t>(head),emit,result.frames.begin()+static_cast<std::ptrdiff_t>(start+written));written+=emit;available-=emit;head+=emit;
                if(received==32){
                    while(requested<changes.size()&&changes[requested].frame<start+read){if(changes[requested].band<3)processor.controls[2-changes[requested].band]=changes[requested].raw;else processor.enabled=changes[requested].raw!=0;++requested;}
                    for(auto& x:collected){float gain=1;if(age<160){fade+=.00625f;gain=fade;}++age;x={(x.l*gain)*gain,(x.r*gain)*gain};}
                    processor.process(collected,pending);received=0;available=32;head=0;
                    if(trace){trace<<(age/32-1);for(auto& b:processor.bands)trace<<' '<<b.raw<<' '<<b.level.target<<' '<<b.threshold<<' '<<b.thresholdTarget<<' '<<b.envelope<<' '<<b.gate;trace<<'\n';}
                }
            }
            start+=count;
        }
    }
#endif
    rmx::writeWav(output,result);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
