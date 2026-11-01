#include "rmx/Engine.h"
#include "rmx/Wav.h"
#include <fstream>
#include <iostream>

struct Targets {
    std::vector<float> values;
    size_t used{};bool exhausted{};
    static float next(void* context) noexcept {
        auto& self=*static_cast<Targets*>(context);
        if(self.used==self.values.size()){self.exhausted=true;return 0;}
        return self.values[self.used++];
    }
};

int main(int argc,char** argv){try{
    if((argc!=4&&argc!=5)||std::filesystem::exists(argv[2]))throw std::runtime_error("Usage: noise_user_probe INPUT NEW_OUTPUT PLAN [RANDOM_TARGETS]");
    std::ifstream file(argv[3]);std::string magic,extra;unsigned version{},frames{},block{},user{},main{},amount{},width{},minimum{},maximum{};
    unsigned sub2{},mode{},wave{},resonance{};
    if(!(file>>magic>>version>>frames>>block>>user>>main>>amount>>width>>minimum>>maximum)||magic!="RMX_NOISE_USER"||(version<1||version>3)
       ||(version>=2&&!(file>>sub2>>mode>>wave>>resonance))
       ||frames<48000||frames>1204*48000||block<8||block>4096||user>1||main>255||amount>255||width>2||minimum>3||maximum>3
       ||sub2>255||mode>1||wave>4||resonance>2||file>>extra)
        throw std::runtime_error("Invalid Noise plan");
    const auto input=rmx::readWav(argv[1],version==3?1204:2);if(input.rate!=48000)throw std::runtime_error("Requires48k");
    if(version<3)for(auto x:input.frames)if(x.l!=0||x.r!=0)throw std::runtime_error("Requires silent input");
    Targets targets;rmx::NoiseModulator::RandomSource source{Targets::next,&targets};
    if(argc==5){
        if(wave!=3||mode!=0||sub2<4)throw std::runtime_error("Target injection requires active Random modulation");
        std::ifstream values(argv[4]);float value;
        while(values>>value){if(!std::isfinite(value)||std::abs(value)>1||targets.values.size()>=40000)throw std::runtime_error("Invalid Random target stream");targets.values.push_back(value);}
        if(!values.eof())throw std::runtime_error("Invalid Random target file");
    }
    rmx::Engine engine;engine.setOutputProtection(false);
    for(auto [p,value]:{std::pair{rmx::Param::AutoTempo,0.f},{rmx::Param::Quantize,0.f},{rmx::Param::SceneType,2.f},
        {rmx::Param::SceneSource,0.f},{rmx::Param::SceneOn,0.f},{rmx::Param::SceneDepth,main/255.f},
        {rmx::Param::SceneTime,amount*7.f/255},{rmx::Param::SceneResonance,sub2/255.f},{rmx::Param::UserSettings,static_cast<float>(user)},
        {rmx::Param::NoiseModMode,static_cast<float>(mode)},{rmx::Param::NoiseWave,static_cast<float>(wave)},{rmx::Param::NoiseResonance,static_cast<float>(resonance)},
        {rmx::Param::NoiseWidth,static_cast<float>(width)},{rmx::Param::NoiseMinimum,static_cast<float>(minimum)},{rmx::Param::NoiseMaximum,static_cast<float>(maximum)}})engine.params.set(p,value);
    engine.prepare(48000,block);rmx::Sample output;output.rate=48000;output.frames.resize(frames);
    if(argc==5)engine.setNoiseRandomSource(&source);
    std::array<float,4096> left{},right{};
    std::array<float,4096> inputLeft{},inputRight{};
    for(unsigned start=0;start<frames;){
        if(start==4800)engine.params.set(rmx::Param::SceneOn,1);
        unsigned count=std::min(block,frames-start);if(start<4800)count=std::min(count,4800-start);
        if(version==3)for(unsigned i=0;i<count;++i){
            const auto x=start+i<input.frames.size()?input.frames[start+i]:rmx::Stereo{};
            inputLeft[i]=x.l;inputRight[i]=x.r;
        }
        engine.process(version==3?inputLeft.data():nullptr,version==3?inputRight.data():nullptr,left.data(),right.data(),count);
        for(unsigned i=0;i<count;++i)output.frames[start+i]={left[i],right[i]};start+=count;
    }
    if(targets.exhausted)throw std::runtime_error("Random target stream exhausted");
    rmx::writeWav(argv[2],output);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
