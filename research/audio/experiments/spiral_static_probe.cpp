// Research-only static Default48k/120BPM Spiral reconstruction. Validation is separate.
#include "rmx/Wav.h"
#include "rmx/FactoryEchoReturn.h"
#include "IsolateNeutral.h"
#include <iostream>

namespace {
using Block=std::array<rmx::Stereo,32>;
using Biquad=rmx::research::IsolateNeutral::Biquad;
struct Pitch {
    std::array<rmx::Stereo,4096> ring{};unsigned writer{},reader{},second{},windowBlocks{},change{};
    float fraction{},window{},fade{},direct{1};bool down{};Biquad filter;
    explicit Pitch(bool direction):reader(4096-(direction?640:1792)),change(direction?48:117),down(direction){
        filter.c={.7878031134605408f,0,-.7878031134605408f,-.42026737332344055f,-.5756062865257263f};
    }
    unsigned wrap(int value)const noexcept{return static_cast<unsigned>(value+8192)%4096;}
    Block read(unsigned& cursor,float& phase,float increment){
        Block result{};
        for(unsigned i=0;i<32;++i){
            if(down){result[i]=ring[wrap(static_cast<int>(cursor)-1)]*phase+ring[cursor]*(1-phase);phase+=increment;if(phase<1)cursor=(cursor+1)%4096;else phase-=1;}
            else{result[i]=ring[cursor]*(1-phase)+ring[(cursor+1)%4096]*phase;phase+=increment;cursor=(cursor+1)%4096;while(phase>=1){phase-=1;cursor=(cursor+1)%4096;}}
        }
        return result;
    }
    void process(const Block& input,Block& output,unsigned raw){
        for(auto x:input){ring[writer]=x;writer=(writer+1)%4096;}
        float increment=down?raw*.003921568859368563f:raw<=129?raw*.007692307699471712f:(raw-130)*.01600000075995922f+1;
        if(change>=9)increment=0;
        const float initial=fraction;auto primary=read(reader,fraction,increment);
        const auto distance=(writer+4096-reader)%4096;
        if(windowBlocks||(down?distance*2>2176:distance*2<3072)){
            if(!windowBlocks)second=wrap(static_cast<int>(reader)+(down?512:-1792));
            float phase=initial;const auto alternate=read(second,phase,increment);
            for(unsigned i=0;i<32;++i){const float complement=1-window,shape=window*complement+.5f,a=(complement*shape)*2,b=(window*shape)*2;primary[i]=primary[i]*a+alternate[i]*b;window+=down?.0022321429569274187f:.002604166977107525f;}
            if(++windowBlocks>=(down?14u:12u)){reader=second;windowBlocks=0;window=0;}
        }
        filter.process(primary,output);
        if(change){
            const float delta=change>5?0.f:.00625f;if(change>5){fade=0;direct=1;}
            for(unsigned i=0;i<32;++i){fade+=delta;direct-=delta;output[i]=input[i]*direct+output[i]*fade;}
            --change;
        }
    }
};
}
int main(int argc,char** argv){try{
    if(argc!=8&&argc!=9)throw std::runtime_error("INPUT NEW_OUTPUT up|down MAIN_RAW SUB1_RAW SUB2_RAW TAIL_SECONDS");
    if(std::filesystem::exists(argv[2]))throw std::runtime_error("Output exists");
    const std::string direction=argv[3];if(direction!="up"&&direction!="down")throw std::runtime_error("Invalid direction");
    const bool down=direction=="down";const int mainRaw=std::stoi(argv[4]),timeRaw=std::stoi(argv[5]),pitchRaw=std::stoi(argv[6]);const double tail=std::stod(argv[7]);
    const unsigned callback=argc==9?static_cast<unsigned>(std::stoul(argv[8])):0;if(argc==9&&(callback<1||callback>4096))throw std::runtime_error("Invalid callback");
    if(mainRaw<0||mainRaw>255||timeRaw<0||timeRaw>255||pitchRaw<0||pitchRaw>255||!std::isfinite(tail)||tail<0||tail>30)throw std::runtime_error("Invalid controls");
    const float position=mainRaw<=3?0.f:(mainRaw-3)*.003968254197388887f;
    const unsigned milliseconds=down?(mainRaw<=3?10:static_cast<unsigned>(position*490.f+10.f)):(mainRaw<=3?100:static_cast<unsigned>(((255-mainRaw)*.003968254197388887f)*95.f+5.f));
    const unsigned delay=milliseconds*48;const float inputGain=std::min(position*4,1.f),loopGain=std::min(position*10,1.f)*(down?.4f:.7f)+.8f,dryGain=down&&position>.5f?2-2*position:1;
    const float outputGain=std::min(1-((1-std::min(static_cast<float>(delay)*1.0416666555101983e-5f,1.f))*.1809999942779541f+.3199999928474426f)*loopGain,.30000001192092896f)*1.4125374555587769f;
    const auto source=rmx::readWav(argv[1],180);if(source.rate!=48000)throw std::runtime_error("Requires 48 kHz");
    rmx::Sample output;output.rate=48000;output.frames.resize(source.frames.size()+std::lround(tail*48000));
    Biquad inputFilter,high,low,post;
    inputFilter.c={.29287490248680115f,.5857498049736023f,.29287490248680115f,-7.176304665877298e-17f,.1714995801448822f};
    high.c={.9682207107543945f,-1.936441421508789f,.9682207107543945f,-1.9362547397613525f,.9366280436515808f};
    low.c={.29549500346183777f,.5909900069236755f,.29549500346183777f,.015271740034222603f,.1667083203792572f};
    post.c={.1419954150915146f,.2839908301830292f,.1419954150915146f,-.19833816587924957f,-.23368017375469208f};
    std::vector<rmx::Stereo> history(196608);unsigned writer=0;Pitch pitch(down);
    rmx::FactoryEchoReturn echoes;echoes.prepare(48000);echoes.restart(rmx::FactoryEchoReturn::Profile::spiral);
    float average=0,held=0,phase=0;bool descending=false;unsigned quiet=0;
    for(size_t base=0;base<output.frames.size();base+=32){
        Block input{},wet{},delayed{};float peak=0;
        for(unsigned i=0;i<32;++i)if(base+i<source.frames.size()){input[i]=source.frames[base+i];peak=std::max(peak,std::abs((input[i].l+input[i].r)*.5f));}
        // The original first active Spiral block follows the shared 32-frame startup.
        if(base==0){for(unsigned i=0;i<32&&i<output.frames.size();++i)output.frames[i]=input[i];continue;}
        const float weighted=average*186.f+peak;average=static_cast<float>(static_cast<double>(weighted)/187.);held=std::max(held,average);
        for(unsigned i=0;i<32;++i)wet[i]=input[i]*inputGain;inputFilter.process(wet,wet);
        for(unsigned i=0;i<32;++i){
            if(descending){phase-=2.0833333564951317e-6f;if(phase< -1){descending=false;phase=-2-phase;}}
            else{phase+=2.0833333564951317e-6f;if(phase>1){descending=true;phase=2-phase;}}
            const int integer=static_cast<int>(phase),whole=integer-(phase<0?1:0);const float fraction=phase-integer+(phase<0?1.f:0.f);
            const auto first=history[(writer+i+196608-delay-whole)%196608],previous=history[(writer+i+196608-delay-whole-1)%196608];
            // Main scales the new input; the settled primary feedback is independent.
            const auto tap=first*(1-fraction)+previous*fraction;wet[i]={std::clamp(wet[i].l+tap.l,-held,held),std::clamp(wet[i].r+tap.r,-held,held)};
        }
        high.process(wet,wet);low.process(wet,wet);
        for(unsigned i=0;i<32;++i)history[(writer+i)%196608]=wet[i]*loopGain;writer=(writer+32)%196608;post.process(wet,wet);
        for(unsigned i=0;i<32;++i){wet[i]=(wet[i]*1.2999999523162842f)*outputGain;++quiet;if(std::abs((wet[i].l+wet[i].r)*.5f)>=held*.001f)quiet=0;}
        if(quiet>=4801){held*=.8912509083747864f;quiet=0;}
        pitch.process(wet,delayed,static_cast<unsigned>(pitchRaw));
        for(unsigned i=0;i<32&&base+i<output.frames.size();++i){const auto y=delayed[i];const auto returned=echoes.process({y.l,y.r},timeRaw,std::clamp((mainRaw-4)*.2f,0.f,1.f),120);output.frames[base+i]={static_cast<float>(input[i].l*dryGain+y.l+returned[0]),static_cast<float>(input[i].r*dryGain+y.r+returned[1])};}
    }
    if(callback){
        // Retain raw input in unfilled callback slots, matching the shared Engine.
        const auto clock=std::move(output.frames);output.frames.assign(clock.size(),{});
        std::copy_n(source.frames.begin(),std::min(source.frames.size(),output.frames.size()),output.frames.begin());
        Block pending{};size_t received=0,available=0,head=0,generated=0;
        for(size_t start=0;start<clock.size();start+=callback){
            const auto count=std::min<size_t>(callback,clock.size()-start);size_t read=0,written=0;
            while(read<count){
                const auto take=std::min(32-received,count-read);received+=take;read+=take;
                const auto emit=std::min(available,count-written);std::copy_n(pending.begin()+static_cast<std::ptrdiff_t>(head),emit,output.frames.begin()+static_cast<std::ptrdiff_t>(start+written));written+=emit;available-=emit;head+=emit;
                if(received==32){for(unsigned i=0;i<32;++i)pending[i]=generated+i<clock.size()?clock[generated+i]:rmx::Stereo{};generated+=32;received=0;available=32;head=0;}
            }
        }
    }
    rmx::writeWav(argv[2],output);std::cout<<delay<<' '<<loopGain<<' '<<outputGain<<'\n';
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
