#include "rmx/Wav.h"
#ifdef RMX_SPIRAL_ENGINE_FIXTURE
#include "rmx/Engine.h"
#elif defined(RMX_SPIRAL_CORE_FIXTURE)
#include "rmx/CalibratedSpiral.h"
#else
#include "../research/audio/experiments/SpiralMotion.h"
#endif
#include <fstream>
#include <iostream>
#include <iomanip>
#include <cstdlib>
int main(int argc,char**argv){try{
    if(argc!=4)throw std::runtime_error("INPUT NEW_OUTPUT SCHEDULE");if(std::filesystem::exists(argv[2]))throw std::runtime_error("Output exists");
    const auto source=rmx::readWav(argv[1],60);if(source.rate!=48000)throw std::runtime_error("Requires 48k");
    std::ifstream file(argv[3]);std::string magic;unsigned version{},direction{},block{},main{},time{},pitch{};
    if(!(file>>magic>>version>>direction>>block>>main>>time>>pitch)||magic!="RMX_SPIRAL_MOTION"||(version!=1&&version!=2)||direction>1||block<1||block>4096||main>255||time>255||pitch>255)throw std::runtime_error("Invalid schedule");
    unsigned initialEnabled=1;if(version==2&&(!(file>>initialEnabled)||initialEnabled>1))throw std::runtime_error("Invalid initial enabled state");
    struct Change{size_t frame;unsigned control,raw;};std::vector<Change> changes;size_t frame{};unsigned control{},raw{};
    while(file>>frame){if(!(file>>control>>raw)||frame>=source.frames.size()||control>4||raw>(control>=3?1u:255u)||(!changes.empty()&&frame<changes.back().frame))throw std::runtime_error("Invalid event");changes.push_back({frame,control,raw});}if(!file.eof())throw std::runtime_error("Malformed schedule");
#ifdef RMX_SPIRAL_ENGINE_FIXTURE
    rmx::Engine engine;engine.setOutputProtection(false);
    engine.params.set(rmx::Param::AutoTempo,0);engine.params.set(rmx::Param::Tempo,120);engine.params.set(rmx::Param::Quantize,0);
    engine.params.set(rmx::Param::IsolateOn,0);engine.params.set(rmx::Param::SceneType,direction?8:3);engine.params.set(rmx::Param::SceneOn,initialEnabled);
    engine.params.set(rmx::Param::SceneDepth,main/255.f);engine.params.set(rmx::Param::SceneTime,time*(7.f/255));engine.params.set(rmx::Param::SceneResonance,pitch/255.f);
    engine.prepare(48000,block);rmx::Sample output;output.rate=48000;output.frames.resize(source.frames.size());
    std::array<float,4096> left{},right{},outLeft{},outRight{};size_t change=0;
    for(size_t start=0;start<source.frames.size();){
        while(change<changes.size()&&changes[change].frame==start){
            const auto& c=changes[change++];switch(c.control){
                case 0:engine.params.set(rmx::Param::SceneDepth,c.raw/255.f);break;
                case 1:engine.params.set(rmx::Param::SceneTime,c.raw*(7.f/255));break;
                case 2:engine.params.set(rmx::Param::SceneResonance,c.raw/255.f);break;
                case 3:engine.params.set(rmx::Param::SceneOn,c.raw);break;
                case 4:engine.params.set(rmx::Param::SceneType,c.raw?8:3);engine.params.set(rmx::Param::SceneOn,1);break;
            }
        }
        size_t count=std::min<size_t>(block,source.frames.size()-start);if(change<changes.size())count=std::min(count,changes[change].frame-start);
        for(size_t i=0;i<count;++i){left[i]=source.frames[start+i].l;right[i]=source.frames[start+i].r;}
        engine.process(left.data(),right.data(),outLeft.data(),outRight.data(),static_cast<uint32_t>(count));
        for(size_t i=0;i<count;++i)output.frames[start+i]={outLeft[i],outRight[i]};start+=count;
    }
    rmx::writeWav(argv[2],output);
#else
#ifdef RMX_SPIRAL_CORE_FIXTURE
    std::vector<rmx::Stereo> storage(rmx::CalibratedSpiral::storageFrames),rawStorage(rmx::CalibratedSpiral::rawStorageFrames);
    rmx::CalibratedSpiral processor;if(!processor.prepare(storage,rawStorage))throw std::runtime_error("Invalid storage");processor.setStorageState(true,true);
    rmx::CalibratedSpiral::Controls controls{main,time,pitch,initialEnabled!=0,static_cast<int>(direction)};
#else
    rmx::research::SpiralMotion processor(direction!=0);rmx::research::SpiralMotion::Controls controls{main,time,pitch,initialEnabled!=0};
#endif
    std::ofstream trace;if(const auto name=std::getenv("RMX_SPIRAL_MOTION_TRACE")){if(std::filesystem::exists(name))throw std::runtime_error("Trace exists");trace.open(name);trace<<std::setprecision(17);}
    rmx::Sample output;output.rate=48000;output.frames=source.frames;std::array<rmx::Stereo,32> collected{},pending{};size_t received=0,available=0,head=0,age=0,requested=0,change=0;float fade=0;
    for(size_t start=0;start<source.frames.size();){
        while(change<changes.size()&&changes[change].frame==start)++change;
        size_t count=std::min<size_t>(block,source.frames.size()-start);if(change<changes.size())count=std::min(count,changes[change].frame-start);size_t read=0,written=0;
        while(read<count){
            const auto take=std::min(32-received,count-read);std::copy_n(source.frames.begin()+static_cast<std::ptrdiff_t>(start+read),take,collected.begin()+static_cast<std::ptrdiff_t>(received));received+=take;read+=take;
            const auto emit=std::min(available,count-written);std::copy_n(pending.begin()+static_cast<std::ptrdiff_t>(head),emit,output.frames.begin()+static_cast<std::ptrdiff_t>(start+written));written+=emit;available-=emit;head+=emit;
            if(received==32){
                while(requested<changes.size()&&changes[requested].frame<start+read){const auto& c=changes[requested++];switch(c.control){case 0:controls.main=c.raw;break;case 1:controls.time=c.raw;break;case 2:controls.pitch=c.raw;break;case 3:controls.enabled=c.raw!=0;break;case 4:controls.direction=static_cast<int>(c.raw);controls.enabled=true;break;}}
                for(auto& x:collected){float gain=1;if(age++<160){fade+=.00625f;gain=fade;}x=(x*gain)*gain;}
#ifdef RMX_SPIRAL_CORE_FIXTURE
                processor.setControls(controls);processor.recordRaw(collected);
#else
                processor.controls=controls;
#endif
                processor.process(collected,pending);
#ifndef RMX_SPIRAL_CORE_FIXTURE
                if(trace)trace<<(age/32-1)<<" "<<processor.currentMain<<" "<<processor.delay<<" "<<processor.velocity<<" "<<processor.acceleration<<" "<<processor.targetVelocity<<" "<<processor.outputGain<<" "<<processor.held<<" "<<processor.average<<" "<<processor.inputGain<<" "<<processor.phase<<" "<<processor.dryGain<<"\n";
#endif
                received=0;available=32;head=0;
            }
        }
        start+=count;
    }
    rmx::writeWav(argv[2],output);
#endif
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
