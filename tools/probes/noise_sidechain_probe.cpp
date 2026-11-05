#include "rmx/CalibratedGateDrive.h"
#include "rmx/NoiseModulator.h"
#include <iostream>
#include <string>

// Bounded binary stdin/stdout adapter. Component records contain threshold +
// 32 detector values; chain input is synthetic interleaved stereo. No audio
// output or manufacturer state is stored by this probe.
int main(int argc,char** argv){try{
    if(argc!=3)throw std::runtime_error("Usage: noise_sidechain_probe --component|--chain RAW");
    const std::string mode=argv[1];const int raw=std::stoi(argv[2]);
    if(raw<0||raw>255||(mode!="--component"&&mode!="--chain"))throw std::runtime_error("Invalid Sidechain request");
    rmx::NoiseModulator motion;rmx::CalibratedGateDrive detector;detector.reset();
    std::array<rmx::Stereo,32> input{},discard{};
    std::array<float,33> driver{};std::array<float,32> peaks{};
    unsigned age=0,blocks=0;float fade=0;
    for(;;){
        auto* data=mode=="--component"?reinterpret_cast<char*>(driver.data()):reinterpret_cast<char*>(input.data());
        const auto bytes=mode=="--component"?sizeof(driver):sizeof(input);
        if(!std::cin.read(data,bytes)){
            if(std::cin.gcount()!=0)throw std::runtime_error("Partial Sidechain record");
            break;
        }
        if(++blocks>15000)throw std::runtime_error("Sidechain probe exceeded bound");
        if(mode=="--chain"){
            for(auto& x:input){
                float gain=1;if(age++<160){fade+=.00625f;gain=fade;}
                x={(x.l*gain)*gain,(x.r*gain)*gain};
            }
            detector.process(input,discard,peaks);driver[0]=detector.lowThreshold();
            std::copy(peaks.begin(),peaks.end(),driver.begin()+1);
            if(age<=4832)continue;
        }else std::copy(driver.begin()+1,driver.end(),peaks.begin());
        const auto& controls=motion.sidechain(raw,peaks,driver[0]);
        if(mode=="--chain")std::cout.write(reinterpret_cast<const char*>(driver.data()),sizeof(driver));
        std::cout.write(reinterpret_cast<const char*>(controls.data()),sizeof(controls));
    }
    if(!std::cout)throw std::runtime_error("Sidechain output failed");
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
