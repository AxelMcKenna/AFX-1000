#include "rmx/Engine.h"
#include "rmx/Wav.h"
#include <fstream>
#include <iostream>

int main(int argc,char** argv){try{
    if(argc!=5)throw std::runtime_error("Usage: drum_roll_probe SILENCE NEW_OUTPUT SCHEDULE NEW_DRY");
    const auto out=std::filesystem::absolute(argv[2]).lexically_normal(),dryPath=std::filesystem::absolute(argv[4]).lexically_normal();
    if(out==dryPath||std::filesystem::exists(out)||std::filesystem::exists(dryPath))throw std::runtime_error("Outputs must be distinct and new");
    const auto input=rmx::readWav(argv[1],30);if(input.rate!=48000)throw std::runtime_error("Drum roll fixture requires48k");
    for(auto x:input.frames)if(x.l!=0||x.r!=0)throw std::runtime_error("Drum roll source must be silent");
    std::ifstream file(argv[3]);std::string magic;unsigned version{},level{},pitch{},rawPosition{},block{},quantize{};double bpm{};
    if(!(file>>magic>>version>>level>>pitch>>rawPosition>>block>>bpm>>quantize)||magic!="RMX_DRUM_ROLL"||version!=1||level>255||pitch>255||rawPosition>255||block<8||block>4096||!std::isfinite(bpm)||bpm<40||bpm>240||quantize>1)
        throw std::runtime_error("Invalid drum roll header");
    struct Change{size_t frame;char type;unsigned value;};std::vector<Change> events;
    int64_t at{};char type{};unsigned value{};
    while(file>>at){
        if(!(file>>type>>value)||at<0||static_cast<size_t>(at)>=input.frames.size()||(!events.empty()&&static_cast<size_t>(at)<events.back().frame)
           ||(type!='H'&&type!='R'&&type!='T'&&type!='X'&&type!='F')||value>((type=='H'||type=='R')?3u:type=='X'?255u:1u))throw std::runtime_error("Invalid drum roll event");
        events.push_back({static_cast<size_t>(at),type,value});
    }
    if(!file.eof()||events.empty())throw std::runtime_error("Invalid/empty drum roll schedule");
    rmx::Engine engine;engine.setOutputProtection(false);
    engine.params.set(rmx::Param::AutoTempo,0);engine.params.set(rmx::Param::Quantize,static_cast<float>(quantize));engine.params.set(rmx::Param::Tempo,static_cast<float>(bpm));
    engine.params.set(rmx::Param::SampleSource,0);engine.params.set(rmx::Param::SceneOn,0);engine.params.set(rmx::Param::IsolateOn,0);
    engine.params.set(rmx::Param::XLevel,level*1.5f/255);engine.params.set(rmx::Param::XPitch,pitch>=128?(pitch-128)*24.f/127:(static_cast<int>(pitch)-128)*24.f/128);
    // Compare equivalent musical settings. The project has eight strip
    // assignments; the original exposes six canonical positions. The two
    // additional project divisions are outside this reference fixture.
    constexpr std::array<unsigned,6> projectPositions{0,1,2,3,5,6};
    auto position=[&](unsigned raw){engine.params.set(rmx::Param::XRoll,static_cast<float>(projectPositions[std::min(5u,raw/51)]));};position(rawPosition);engine.prepare(48000,block);
    rmx::Sample audio,dry;audio.rate=dry.rate=48000;audio.frames.resize(input.frames.size());dry.frames.resize(input.frames.size());
    std::array<float,4096> left{},right{};size_t event=0;unsigned selected=0;
    for(size_t start=0;start<input.frames.size();){
        while(event<events.size()&&events[event].frame==start){
            const auto e=events[event++];
            if(e.type=='H'){selected=e.value;engine.enqueue({rmx::EventType::Trigger,static_cast<uint8_t>(selected),1,0,0,0});}
            else if(e.type=='T')engine.enqueue({e.value?rmx::EventType::RollStart:rmx::EventType::RollStop,static_cast<uint8_t>(selected)});
            else if(e.type=='X')position(e.value);
            else if(e.type=='F'){engine.params.set(rmx::Param::XHold,static_cast<float>(e.value));if(!e.value)engine.enqueue({rmx::EventType::RollStop});}
        }
        size_t count=std::min<size_t>(block,input.frames.size()-start);if(event<events.size())count=std::min(count,events[event].frame-start);
        engine.process(nullptr,nullptr,left.data(),right.data(),static_cast<uint32_t>(count));
        for(size_t i=0;i<count;++i)audio.frames[start+i]={left[i],right[i]};start+=count;
    }
    rmx::writeWav(out,audio);rmx::writeWav(dryPath,dry);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
