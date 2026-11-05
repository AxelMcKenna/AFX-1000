#include "rmx/Wav.h"
#include "rmx/CalibratedReverbDown.h"
#ifdef RMX_REVERB_ENGINE_FIXTURE
#include "rmx/Engine.h"
#endif
#include <fstream>
#include <iostream>
#include <sstream>
namespace {
struct Controls {int main{128},amount{128},cutoff{},enabled{1};};
struct Event {size_t frame{};std::string control;int value{};};
struct Plan {Controls initial;double tail{};size_t block{128};std::vector<Event> events;};
void valid(const Controls& c) {
    if(c.main<0||c.main>255||c.amount<0||c.amount>255||c.cutoff<0||c.cutoff>255||c.enabled<0||c.enabled>1)
        throw std::runtime_error("Controls outside static raw map");
}
void apply(Controls& c,const Event& e) {
    if(e.control=="main")c.main=e.value;
    else if(e.control=="amount")c.amount=e.value;
    else if(e.control=="cutoff")c.cutoff=e.value;
    else if(e.control=="enabled")c.enabled=e.value;
    else throw std::runtime_error("Unknown event control");
    valid(c);
}
Plan readPlan(const std::filesystem::path& path) {
    std::ifstream f(path);std::string text;Plan plan;size_t line=0;Controls test;bool blockSeen=false;
    if(!f)throw std::runtime_error("Cannot open motion schedule");
    while(std::getline(f,text)) {
        std::istringstream row(text);std::string kind,extra;row>>kind;
        if(line==0) {int version{};if(kind!="RMX_REVERB_MOTION"||!(row>>version)||version!=1)throw std::runtime_error("Invalid motion schema");}
        else if(line==1) {
            if(kind!="initial"||!(row>>plan.initial.main>>plan.initial.amount>>plan.initial.cutoff>>plan.initial.enabled))
                throw std::runtime_error("Invalid initial controls");
            valid(plan.initial);test=plan.initial;
        } else if(line==2) {
            if(kind!="tail"||!(row>>plan.tail)||!std::isfinite(plan.tail)||plan.tail<0||plan.tail>120)
                throw std::runtime_error("Invalid tail");
        } else {
            if(kind=="block"){
                if(blockSeen||!(row>>plan.block)||plan.block<8||plan.block>4096||!plan.events.empty())
                    throw std::runtime_error("Invalid callback block size");
                blockSeen=true;
                if(row>>extra)throw std::runtime_error("Unexpected callback field");
                ++line;continue;
            }
            int64_t frame{};Event e;
            if(kind!="event"||!(row>>frame>>e.control>>e.value)||frame<0)
                throw std::runtime_error("Invalid event");
            e.frame=static_cast<size_t>(frame);
            if(!plan.events.empty()&&e.frame<plan.events.back().frame)throw std::runtime_error("Events must be ordered");
            apply(test,e);plan.events.push_back(std::move(e));
        }
        if(row>>extra)throw std::runtime_error("Unexpected schedule field");
        ++line;
    }
    if(line<3)throw std::runtime_error("Incomplete motion schedule");
    return plan;
}
}
int main(int argc,char** argv){try {
    if((argc!=12&&argc!=13)||std::string(argv[4])!="faded"||std::string(argv[5])!="post"||std::string(argv[6])!="read"||std::string(argv[7])!="32"||std::string(argv[9])!="output"||std::string(argv[10])!="0"||std::string(argv[11])!="startup"||(argc==13&&std::string(argv[12])!="0"))
        throw std::runtime_error("Production fixture requires faded/post/read/32/output/0/startup/0");
    if(std::filesystem::exists(argv[2])||std::filesystem::exists(argv[8]))throw std::runtime_error("Output and dry trace must be new");
    const auto plan=readPlan(argv[3]);const auto input=rmx::readWav(argv[1],180);
    if(input.rate!=48000)throw std::runtime_error("Production Down fixture requires 48 kHz");
    rmx::Sample output,dry;output.rate=dry.rate=48000;output.frames.resize(input.frames.size()+static_cast<size_t>(std::llround(plan.tail*48000)));dry.frames.resize(output.frames.size());
    for(const auto& e:plan.events)if(e.frame>=output.frames.size())throw std::runtime_error("Event outside render extent");
    rmx::CalibratedReverbDown processor;processor.prepare(plan.block);Controls target=plan.initial;size_t event=0;
    std::array<rmx::Stereo,4096> in{},out{},trace{};
#ifdef RMX_REVERB_ENGINE_FIXTURE
    rmx::Engine engine;engine.params.set(rmx::Param::AutoTempo,0);engine.params.set(rmx::Param::Tempo,120);
    engine.params.set(rmx::Param::SceneType,9);engine.params.set(rmx::Param::IsolateOn,0);
    engine.params.set(rmx::Param::SceneSource,0);engine.prepare(48000,static_cast<uint32_t>(plan.block));
    std::array<float,4096> left{},right{},outputLeft{},outputRight{};
#endif
    for(size_t start=0;start<output.frames.size();){
        while(event<plan.events.size()&&plan.events[event].frame==start){apply(target,plan.events[event]);++event;}
        size_t count=std::min(plan.block,output.frames.size()-start);
        if(event<plan.events.size())count=std::min(count,plan.events[event].frame-start);
        for(size_t i=0;i<count;++i)in[i]=start+i<input.frames.size()?input.frames[start+i]:rmx::Stereo{};
        processor.setControls({target.main,target.amount,target.cutoff,target.enabled!=0});
        if(!processor.process(std::span<const rmx::Stereo>(in.data(),count),std::span<rmx::Stereo>(out.data(),count),std::span<rmx::Stereo>(trace.data(),count)))throw std::runtime_error("Production callback rejected extent");
#ifdef RMX_REVERB_ENGINE_FIXTURE
        engine.params.set(rmx::Param::SceneDepth,target.main/255.f);
        engine.params.set(rmx::Param::SceneTime,target.amount*7.f/255);
        engine.params.set(rmx::Param::SceneResonance,target.cutoff/255.f);
        engine.params.set(rmx::Param::SceneOn,static_cast<float>(target.enabled));
        for(size_t i=0;i<count;++i){left[i]=in[i].l;right[i]=in[i].r;}
        engine.process(left.data(),right.data(),outputLeft.data(),outputRight.data(),static_cast<uint32_t>(count));
        if(engine.latencySamples()!=32)throw std::runtime_error("Engine Down nominal latency differs");
        for(size_t i=0;i<count;++i)out[i]={outputLeft[i],outputRight[i]};
#endif
        std::copy_n(out.begin(),count,output.frames.begin()+static_cast<std::ptrdiff_t>(start));std::copy_n(trace.begin(),count,dry.frames.begin()+static_cast<std::ptrdiff_t>(start));start+=count;
    }
    rmx::writeWav(argv[2],output);rmx::writeWav(argv[8],dry);std::cout<<"Rendered bounded production Down block processor\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
