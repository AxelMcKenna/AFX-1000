#include "rmx/Engine.h"
#include "rmx/Wav.h"
#include <fstream>
#include <iostream>

namespace {
constexpr double rate=48000;
constexpr uint32_t block=128;
void save(const std::filesystem::path& directory,const std::string& name,rmx::Sample& sample,std::ofstream& manifest) {
    double energy=0;float peak=0;
    for(auto frame:sample.frames) {energy+=double(frame.l)*frame.l+double(frame.r)*frame.r;peak=std::max(peak,rmx::peak(frame));}
    size_t activeFrames=sample.frames.size();
    while(activeFrames>1&&rmx::peak(sample.frames[activeFrames-1])<peak*.001f)--activeFrames;
    const double rms=std::sqrt(energy/(activeFrames*2));
    // One constant gain for the whole clip, preserving transient shape/tails.
    // Conservative audition level; the manifest records any peak-limited match.
    const double gain=std::min(.9/std::max(1.e-12,double(peak)),.05/std::max(1.e-12,rms));
    for(auto& frame:sample.frames)frame=frame*static_cast<float>(gain);
    rmx::writeWav(directory/(name+".wav"),sample);
    manifest<<name<<".wav,"<<gain<<','<<peak*gain<<','<<rms*gain<<'\n';
}
rmx::Sample render(const rmx::SampleBank& bank,int pad,float pitch,bool roll,bool noise) {
    rmx::Engine engine;engine.setBank(&bank);
    engine.params.set(rmx::Param::XPitch,pitch);engine.params.set(rmx::Param::SampleSource,0);
    engine.params.set(rmx::Param::XLevel,.60f);engine.params.set(rmx::Param::AutoTempo,0);
    engine.params.set(rmx::Param::SceneType,2);engine.params.set(rmx::Param::SceneTime,5);
    engine.params.set(rmx::Param::SceneResonance,0);engine.params.set(rmx::Param::SceneDepth,0);
    engine.params.set(rmx::Param::SceneOn,noise?1:0);engine.prepare(rate,block);
    rmx::Sample output;output.rate=rate;output.frames.resize(static_cast<size_t>(rate*(noise?10:roll?4:3)));
    std::array<float,block> left{},right{};
    for(size_t offset=0;offset<output.frames.size();offset+=block) {
        const auto count=static_cast<uint32_t>(std::min(size_t{block},output.frames.size()-offset));
        std::array<rmx::Event,2> events{};size_t eventCount=0;
        if(!noise) {
            const size_t spacing=static_cast<size_t>(rate*.125),first=roll?((offset+spacing-1)/spacing)*spacing:0;
            if(first>=offset&&first<offset+count&&(!roll||first<static_cast<size_t>(rate*2)))
                events[eventCount++]={rmx::EventType::Trigger,static_cast<uint8_t>(pad),1,static_cast<uint32_t>(first-offset)};
        } else {
            const double seconds=offset/rate;
            engine.params.set(rmx::Param::SceneDepth,static_cast<float>(std::clamp((seconds-.25)/6,0.,1.)));
            if(seconds>6.5)engine.params.set(rmx::Param::SceneOn,0);
        }
        engine.process(nullptr,nullptr,left.data(),right.data(),count,{},std::span(events).first(eventCount));
        for(size_t i=0;i<count;++i)output.frames[offset+i]={left[i],right[i]};
    }
    return output;
}
}
int main(int argc,char** argv) {
    if(argc!=2) {std::cerr<<"Usage: rmx_sound_preview new-output-directory\n";return 2;}
    try {
        const std::filesystem::path directory=argv[1];
        if(std::filesystem::exists(directory))throw std::runtime_error("Output already exists; choose a new directory");
        std::filesystem::create_directories(directory);
        std::ofstream manifest(directory/"manifest.csv");manifest<<"file,constant_gain,peak,active_rms\n";
        const auto bank=rmx::makeFactoryBank(rate,false);
        constexpr std::array<const char*,4> names{"kick","snare","clap","hat"};
        for(int pad=0;pad<4;++pad) {
            for(int pitch:{-12,0,12,24}) {
                auto sample=render(bank,pad,static_cast<float>(pitch),false,false);
                save(directory,std::string(names[pad])+"_pitch_"+std::to_string(pitch),sample,manifest);
            }
            auto sample=render(bank,pad,0,true,false);save(directory,std::string(names[pad])+"_roll",sample,manifest);
        }
        auto noise=render(bank,0,0,false,true);save(directory,"noise_sweep",noise,manifest);
        if(!manifest)throw std::runtime_error("Cannot write preview manifest");
        std::cout<<"Wrote 21 offline audition clips to "<<directory<<" (no audio device opened)\n";
    } catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
