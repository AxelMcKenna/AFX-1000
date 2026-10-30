#include "rmx/Engine.h"
#include "rmx/Wav.h"
#include <fstream>
#include <iostream>

int main(int argc,char** argv){try{
    if(argc!=5)throw std::runtime_error("Usage: drum_performance_probe SILENCE NEW_OUTPUT SCHEDULE NEW_DRY");
    const auto output=std::filesystem::absolute(argv[2]).lexically_normal(),dryPath=std::filesystem::absolute(argv[4]).lexically_normal();
    if(output==dryPath||std::filesystem::exists(output)||std::filesystem::exists(dryPath))throw std::runtime_error("Outputs must be distinct and new");
    const auto input=rmx::readWav(argv[1],30);if(input.rate!=48000)throw std::runtime_error("Performance fixture requires48k");
    for(auto x:input.frames)if(x.l!=0||x.r!=0)throw std::runtime_error("Performance source must be silent");
    std::ifstream file(argv[3]);std::string magic;unsigned version{},level{},pitch{},position{},block{},quantize{},automatic{},hold{},overdub{};double bpm{};
    if(!(file>>magic>>version>>level>>pitch>>position>>block>>bpm>>quantize>>automatic>>hold>>overdub)||magic!="RMX_DRUM_PERFORMANCE"||(version!=1&&version!=2)||level>255||pitch>255||position>255||block<8||block>4096||!std::isfinite(bpm)||bpm<40||bpm>240||quantize>1||automatic>1||hold>1||overdub>1)
        throw std::runtime_error("Invalid performance header");
    unsigned user{},effect{1},route{1},depth{},amount{},cutoff{},enabled{};
    struct Profile{unsigned gain{3},decay{1},envelope{};};std::array<Profile,4> profiles{};
    if(version==2){
        if(!(file>>user>>effect>>route>>depth>>amount>>cutoff>>enabled)||user>1||effect>9||route>3||depth>255||amount>255||cutoff>255||enabled>1)
            throw std::runtime_error("Invalid combined performance controls");
        for(auto& profile:profiles)if(!(file>>profile.gain>>profile.decay>>profile.envelope)||profile.gain>6||profile.decay>2||profile.envelope>1)
            throw std::runtime_error("Invalid combined drum profile");
    }
    struct Change{size_t frame;char type;unsigned value;};std::vector<Change> events;int64_t at{};char type{};unsigned value{};
    while(file>>at){
        if(!(file>>type>>value)||at<0||static_cast<size_t>(at)>=input.frames.size()||(!events.empty()&&static_cast<size_t>(at)<events.back().frame)
            ||std::string_view("HRTXFLPQAOMDEVBC").find(type)==std::string_view::npos||value>((type=='H'||type=='R')?3u:(type=='X'||type=='L'||type=='P'||type=='V'||type=='B'||type=='C')?255u:1u))throw std::runtime_error("Invalid performance event");
        events.push_back({static_cast<size_t>(at),type,value});
    }
    if(!file.eof()||events.empty())throw std::runtime_error("Invalid/empty performance schedule");
    rmx::Engine engine;engine.setOutputProtection(false);
    engine.params.set(rmx::Param::AutoTempo,automatic);engine.params.set(rmx::Param::Quantize,quantize);engine.params.set(rmx::Param::Tempo,static_cast<float>(bpm));
    engine.params.set(rmx::Param::SampleSource,0);engine.params.set(rmx::Param::SceneOn,0);engine.params.set(rmx::Param::IsolateOn,0);engine.params.set(rmx::Param::XHold,hold);engine.params.set(rmx::Param::Overdub,overdub);
    if(version==2){
        engine.params.set(rmx::Param::UserSettings,user);
        engine.params.set(rmx::Param::SceneType,effect);engine.params.set(rmx::Param::SceneSource,route);
        engine.params.set(rmx::Param::SceneDepth,depth/255.f);engine.params.set(rmx::Param::SceneTime,amount*7.f/255);
        engine.params.set(rmx::Param::SceneResonance,cutoff/255.f);engine.params.set(rmx::Param::SceneOn,enabled);
        for(unsigned pad=0;pad<4;++pad){
            engine.params.set(static_cast<rmx::Param>(static_cast<unsigned>(rmx::Param::KickGain)+pad),3.f-profiles[pad].gain);
            engine.params.set(static_cast<rmx::Param>(static_cast<unsigned>(rmx::Param::KickDecay)+pad),profiles[pad].decay);
            engine.params.set(static_cast<rmx::Param>(static_cast<unsigned>(rmx::Param::KickEnvelope)+pad),profiles[pad].envelope);
        }
    }
    const auto setPitch=[&](unsigned raw){engine.params.set(rmx::Param::XPitch,raw>=128?(raw-128)*24.f/127:(static_cast<int>(raw)-128)*24.f/128);};
    engine.params.set(rmx::Param::XLevel,level*1.5f/255);setPitch(pitch);
    constexpr std::array<unsigned,6> positions{0,1,2,3,5,6};unsigned currentPosition=position;
    const auto setPosition=[&](unsigned raw){currentPosition=raw;engine.params.set(rmx::Param::XRoll,static_cast<float>(positions[std::min(5u,raw/51)]));};setPosition(position);engine.prepare(48000,block);
    rmx::Sample audio,dry;audio.rate=dry.rate=48000;audio.frames.resize(input.frames.size());dry.frames.resize(input.frames.size());
    std::array<float,4096> left{},right{};size_t event=0;unsigned selected=0;bool mute=false,erase=false,touched=false;
    for(size_t start=0;start<input.frames.size();){
        while(event<events.size()&&events[event].frame==start){const auto e=events[event++];
            switch(e.type){
            case 'H':selected=e.value;engine.enqueue({erase?rmx::EventType::DeletePad:mute?rmx::EventType::MutePad:rmx::EventType::Trigger,static_cast<uint8_t>(selected),1,0,0,0});break;
            case 'T':touched=e.value!=0;engine.enqueue({e.value&&currentPosition>=51?rmx::EventType::RollStart:rmx::EventType::RollStop,static_cast<uint8_t>(selected)});break;
            case 'X':setPosition(e.value);engine.enqueue({rmx::EventType::RollPosition});break;
            case 'F':engine.params.set(rmx::Param::XHold,e.value);if(!e.value&&!touched)engine.enqueue({rmx::EventType::RollStop});break;
            case 'L':engine.params.set(rmx::Param::XLevel,e.value*1.5f/255);break;
            case 'P':setPitch(e.value);break;
            case 'Q':engine.params.set(rmx::Param::Quantize,e.value);break;
            case 'A':automatic=e.value;engine.params.set(rmx::Param::AutoTempo,e.value);break;
            case 'O':engine.params.set(rmx::Param::Overdub,e.value);break;
            case 'E':engine.params.set(rmx::Param::SceneOn,e.value);break;
            case 'V':engine.params.set(rmx::Param::SceneDepth,e.value/255.f);break;
            case 'B':engine.params.set(rmx::Param::SceneTime,e.value*7.f/255);break;
            case 'C':engine.params.set(rmx::Param::SceneResonance,e.value/255.f);break;
            case 'M':mute=e.value;break;case 'D':erase=e.value;break;default:break;
            }
        }
        size_t count=std::min<size_t>(block,input.frames.size()-start);if(event<events.size())count=std::min(count,events[event].frame-start);
        const rmx::Transport transport{bpm,static_cast<double>(start)/48000*bpm/60,automatic!=0,true};
        engine.process(nullptr,nullptr,left.data(),right.data(),static_cast<uint32_t>(count),transport);
        for(size_t i=0;i<count;++i)audio.frames[start+i]={left[i],right[i]};start+=count;
    }
    rmx::writeWav(output,audio);rmx::writeWav(dryPath,dry);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
