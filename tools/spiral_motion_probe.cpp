#include "rmx/Wav.h"
#include "../research/audio/experiments/SpiralMotion.h"
#include <fstream>
#include <iostream>
#include <iomanip>
#include <cstdlib>
int main(int argc,char**argv){try{
    if(argc!=4)throw std::runtime_error("INPUT NEW_OUTPUT SCHEDULE");if(std::filesystem::exists(argv[2]))throw std::runtime_error("Output exists");
    const auto source=rmx::readWav(argv[1],60);if(source.rate!=48000)throw std::runtime_error("Requires 48k");
    std::ifstream file(argv[3]);std::string magic;unsigned version{},direction{},block{},main{},time{},pitch{};
    if(!(file>>magic>>version>>direction>>block>>main>>time>>pitch)||magic!="RMX_SPIRAL_MOTION"||version!=1||direction>1||block<1||block>4096||main>255||time>255||pitch>255)throw std::runtime_error("Invalid schedule");
    struct Change{size_t frame;unsigned control,raw;};std::vector<Change> changes;size_t frame{};unsigned control{},raw{};
    while(file>>frame){if(!(file>>control>>raw)||frame>=source.frames.size()||control>3||raw>(control==3?1u:255u)||(!changes.empty()&&frame<changes.back().frame))throw std::runtime_error("Invalid event");changes.push_back({frame,control,raw});}if(!file.eof())throw std::runtime_error("Malformed schedule");
    rmx::research::SpiralMotion processor(direction!=0);processor.controls={main,time,pitch,true};
    std::ofstream trace;if(const auto name=std::getenv("RMX_SPIRAL_MOTION_TRACE")){if(std::filesystem::exists(name))throw std::runtime_error("Trace exists");trace.open(name);trace<<std::setprecision(17);}
    rmx::Sample output;output.rate=48000;output.frames=source.frames;std::array<rmx::Stereo,32> collected{},pending{};size_t received=0,available=0,head=0,age=0,requested=0,change=0;float fade=0;
    for(size_t start=0;start<source.frames.size();){
        while(change<changes.size()&&changes[change].frame==start)++change;
        size_t count=std::min<size_t>(block,source.frames.size()-start);if(change<changes.size())count=std::min(count,changes[change].frame-start);size_t read=0,written=0;
        while(read<count){
            const auto take=std::min(32-received,count-read);std::copy_n(source.frames.begin()+static_cast<std::ptrdiff_t>(start+read),take,collected.begin()+static_cast<std::ptrdiff_t>(received));received+=take;read+=take;
            const auto emit=std::min(available,count-written);std::copy_n(pending.begin()+static_cast<std::ptrdiff_t>(head),emit,output.frames.begin()+static_cast<std::ptrdiff_t>(start+written));written+=emit;available-=emit;head+=emit;
            if(received==32){
                while(requested<changes.size()&&changes[requested].frame<start+read){const auto& c=changes[requested++];switch(c.control){case 0:processor.controls.main=c.raw;break;case 1:processor.controls.time=c.raw;break;case 2:processor.controls.pitch=c.raw;break;case 3:processor.controls.enabled=c.raw!=0;break;}}
                for(auto& x:collected){float gain=1;if(age++<160){fade+=.00625f;gain=fade;}x=(x*gain)*gain;}
                processor.process(collected,pending);if(trace)trace<<(age/32-1)<<" "<<processor.currentMain<<" "<<processor.delay<<" "<<processor.velocity<<" "<<processor.acceleration<<" "<<processor.targetVelocity<<" "<<processor.outputGain<<" "<<processor.held<<" "<<processor.average<<" "<<processor.inputGain<<" "<<processor.phase<<" "<<processor.dryGain<<"\n";received=0;available=32;head=0;
            }
        }
        start+=count;
    }
    rmx::writeWav(argv[2],output);
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
