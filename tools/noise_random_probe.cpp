#include "rmx/NoiseModulator.h"
#include <cmath>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

struct Draws {
    std::vector<float> values;
    size_t used{};
    bool exhausted{};
    static float next(void* state) noexcept {
        auto& self=*static_cast<Draws*>(state);
        if(self.used==self.values.size()){self.exhausted=true;return 0;}
        return self.values[self.used++];
    }
};
int main(int argc,char** argv){try{
    const bool bins=argc==7&&std::string(argv[1])=="--bins";
    if(argc!=5&&!bins)throw std::runtime_error("Usage: noise_random_probe RAW BLOCKS TARGETS_OR_OWN controls|targets OR --bins RAW TARGETS_OR_OWN START STEP COUNT");
    int start=0,step=0,count=0;
    if(bins){start=std::stoi(argv[4]);step=std::stoi(argv[5]);count=std::stoi(argv[6]);}

    const int raw=std::stoi(argv[bins?2:1]);
    if(bins&&(raw<4||start<0||step<1||step>4096||count<1||count>500000||static_cast<int64_t>(start)+static_cast<int64_t>(count)*step>7204*48000))throw std::runtime_error("Invalid Random bin request");
    const int blocks=bins?static_cast<int>((static_cast<int64_t>(start)+(count-1)*static_cast<int64_t>(step))/32+1):std::stoi(argv[2]);
    const std::string mode=bins?"bins":argv[4];
    if(raw<0||raw>255||blocks<1||blocks>10806000||(mode!="controls"&&mode!="targets"&&mode!="bins"))throw std::runtime_error("Invalid bounded Random request");
    if(mode=="controls"&&blocks>15000)throw std::runtime_error("Full control output is limited to ten seconds");
    Draws draws;rmx::NoiseModulator::RandomSource source{Draws::next,&draws};
    const bool own=std::string(argv[3])=="own";
    if(!own){
        std::ifstream file(argv[3]);float value;
        while(file>>value){if(!std::isfinite(value)||std::abs(value)>1||draws.values.size()>=200000)throw std::runtime_error("Invalid target stream");draws.values.push_back(value);}
        if(!file.eof())throw std::runtime_error("Invalid target text");
    }
    rmx::NoiseModulator model;int emitted=0;
    const float depth=raw-3<40?(raw-3)*.025f:1.f;
    for(int block=0;block<blocks;++block){
        const auto before=model.randomDrawCount();
        const auto& values=model.generate(raw,3,false,own?nullptr:&source);
        if(mode=="controls")std::cout.write(reinterpret_cast<const char*>(values.data()),sizeof(values));
        else if(mode=="bins"){
            while(emitted<count&&(start+emitted*step)/32==block){
                const int frame=start+emitted*step;
                const float value=values[frame%32<16?0:16]/depth;
                const uint8_t bin=static_cast<uint8_t>(std::clamp(static_cast<int>((value+1)*2),0,3));
                std::cout.write(reinterpret_cast<const char*>(&bin),1);++emitted;
            }
        }
        else if(model.randomDrawCount()!=before){const auto value=model.randomTargetValue();std::cout.write(reinterpret_cast<const char*>(&value),sizeof(value));}
    }
    if(bins&&emitted!=count)throw std::runtime_error("Wrong Random label extent");
    if(draws.exhausted)throw std::runtime_error("Observed target stream exhausted");
    if(!std::cout)throw std::runtime_error("Random output failed");
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
