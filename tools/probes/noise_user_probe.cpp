#include "rmx/Engine.h"
#include "rmx/Wav.h"
#include <fstream>
#include <iostream>
#include <chrono>
#include <thread>

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
    unsigned sub2{},mode{},wave{},resonance{},repeatInput{},captureStart{},captureFrames{},warmupFrames{},segmentFrames{},chunkCount{};
    if(!(file>>magic>>version>>frames>>block>>user>>main>>amount>>width>>minimum>>maximum)||magic!="RMX_NOISE_USER"||(version<1||version>5)
       ||(version>=2&&!(file>>sub2>>mode>>wave>>resonance))
       ||(version==4&&!(file>>repeatInput>>captureStart>>captureFrames))
       ||(version==5&&!(file>>repeatInput>>warmupFrames>>segmentFrames>>chunkCount))
       ||frames<48000||frames>(version>=4?7204u:1204u)*48000||block<8||block>4096||user>1||main>255||amount>255||width>2||minimum>3||maximum>3
       ||sub2>255||mode>1||wave>4||resonance>2||file>>extra)
        throw std::runtime_error("Invalid Noise plan");
    if(version<4)captureFrames=frames;
    if(version==5){
        if(warmupFrames>4u*48000||segmentFrames<48000||segmentFrames>1200u*48000||chunkCount<1||chunkCount>6
            ||frames!=warmupFrames+segmentFrames*chunkCount)
            throw std::runtime_error("Invalid Noise batch extent");
        captureFrames=warmupFrames+segmentFrames;
    }
    if(repeatInput>1||captureFrames==0||captureFrames>1204u*48000||captureStart>frames||captureFrames>frames-captureStart)
        throw std::runtime_error("Invalid Noise capture window");
    const auto input=rmx::readWav(argv[1],version>=3?1204:2);if(input.rate!=48000||input.frames.empty())throw std::runtime_error("Requires nonempty48k input");
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
    engine.prepare(48000,block);rmx::Sample output;output.rate=48000;output.frames.resize(captureFrames);
    const std::filesystem::path batchDirectory(argv[2]);
    unsigned batchIndex=0,batchUsed=0;
    if(version==5&&!std::filesystem::create_directory(batchDirectory))throw std::runtime_error("Cannot create Noise batch directory");
    const auto flushBatch=[&]{
        const auto stem=batchDirectory/std::to_string(batchIndex);
        rmx::writeWav(stem.string()+".wav",output);
        std::ofstream(stem.string()+".ready").close();
        const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(1800);
        while(!std::filesystem::exists(stem.string()+".ack")){
            if(std::chrono::steady_clock::now()>deadline)throw std::runtime_error("Noise batch consumer timed out");
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
        }
        if(std::filesystem::exists(stem.string()+".wav"))throw std::runtime_error("Noise batch consumer retained audio");
        std::filesystem::remove(stem.string()+".ack");std::filesystem::remove(stem.string()+".ready");
        ++batchIndex;
        if(batchIndex<chunkCount){
            std::array<rmx::Stereo,128> tail;std::copy(output.frames.end()-128,output.frames.end(),tail.begin());
            output.frames.resize(segmentFrames+128);std::copy(tail.begin(),tail.end(),output.frames.begin());batchUsed=128;
        }
    };
    if(argc==5)engine.setNoiseRandomSource(&source);
    std::array<float,4096> left{},right{};
    std::array<float,4096> inputLeft{},inputRight{};
    for(unsigned start=0;start<frames;){
        if(start==4800)engine.params.set(rmx::Param::SceneOn,1);
        unsigned count=std::min(block,frames-start);if(start<4800)count=std::min(count,4800-start);
        if(version>=3)for(unsigned i=0;i<count;++i){
            const auto index=repeatInput?(start+i)%input.frames.size():start+i;
            const auto x=index<input.frames.size()?input.frames[index]:rmx::Stereo{};
            inputLeft[i]=x.l;inputRight[i]=x.r;
        }
        engine.process(version>=3?inputLeft.data():nullptr,version>=3?inputRight.data():nullptr,left.data(),right.data(),count);
        for(unsigned i=0;i<count;++i){
            if(version==5){output.frames[batchUsed++]={left[i],right[i]};if(batchUsed==output.frames.size())flushBatch();}
            else if(start+i>=captureStart&&start+i-captureStart<captureFrames)output.frames[start+i-captureStart]={left[i],right[i]};
        }
        start+=count;
    }
    if(targets.exhausted)throw std::runtime_error("Random target stream exhausted");
    if(version==5){if(batchIndex!=chunkCount)throw std::runtime_error("Noise batch incomplete");std::ofstream(batchDirectory/"complete").close();}
    else rmx::writeWav(argv[2],output);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
