#include "rmx/NoiseModulator.h"
#include <iostream>
#include <string>

int main(int argc,char** argv){try{
    if(argc==7&&std::string(argv[1])=="--bins"){
        const int raw=std::stoi(argv[2]),wave=std::stoi(argv[3]),start=std::stoi(argv[4]),step=std::stoi(argv[5]),count=std::stoi(argv[6]);
        if(raw<4||raw>255||wave<0||wave>2||start<0||step<1||step>4096||count<1||count>500000
            ||static_cast<int64_t>(start)+static_cast<int64_t>(count)*step>1204*48000)
            throw std::runtime_error("Invalid bounded profile request");
        rmx::NoiseModulator model;int block=-1;
        const float depth=raw-3<40?(raw-3)*.025f:1.f;
        const std::array<float,32>* controls=nullptr;
        for(int i=0;i<count;++i){
            const int frame=start+i*step;
            while(block<frame/32){controls=&model.generate(raw,wave);++block;}
            const float value=(*controls)[frame%32<16?0:16]/depth;
            const uint8_t bin=wave==2?(value<-.8f?0:value>.8f?2:1):static_cast<uint8_t>(std::clamp(static_cast<int>((value+1)*2),0,3));
            std::cout.write(reinterpret_cast<const char*>(&bin),1);
        }
        if(!std::cout)throw std::runtime_error("Profile output failed");
        return 0;
    }
    if(argc!=4)throw std::runtime_error("Usage: noise_motion_probe RAW WAVE BLOCKS");
    const int raw=std::stoi(argv[1]),wave=std::stoi(argv[2]),blocks=std::stoi(argv[3]);
    if(raw<0||raw>255||wave<0||wave>3||blocks<1||blocks>15000)throw std::runtime_error("Invalid bounded control request");
    rmx::NoiseModulator model;
    for(int i=0;i<blocks;++i){const auto& values=model.generate(raw,wave);std::cout.write(reinterpret_cast<const char*>(values.data()),sizeof(values));}
    if(!std::cout)throw std::runtime_error("Control output failed");
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
