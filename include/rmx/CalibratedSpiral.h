#pragma once
#include "rmx/Dsp.h"
#include <array>
#include <cstdint>
#include <span>

namespace rmx {
// Default48k/manual120 Spiral, on the shared32-frame source clock.
// Long storage is borrowed from legacy Scene buffers; no callback allocation.
class CalibratedSpiral {
public:
    struct Controls {unsigned main{128},time{},pitch{};bool enabled{true};int direction{-1};};
    static constexpr size_t rawStorageFrames=32768;
    static constexpr size_t storageFrames=32768+4096+4*24004;
    bool prepare(std::span<Stereo> storage,std::span<Stereo> rawStorage) noexcept;
    void reset() noexcept;
    void setStorageState(bool active,bool rawAvailable) noexcept;
    void setControls(Controls target) noexcept;
    void recordRaw(std::span<const Stereo,32> input) noexcept;
    void process(std::span<const Stereo,32> input,std::span<Stereo,32> output) noexcept;
private:
    using Block=std::array<Stereo,32>;
    struct Biquad {
        std::array<float,5> c{};std::array<float,4> state{};
        void process(std::span<const Stereo,32> input,std::span<Stereo,32> output) noexcept {
            bool quiet=true;for(auto x:input)quiet&=std::abs(x.l)<1e-37&&std::abs(x.r)<1e-37;
            for(unsigned ch=0;ch<2;++ch){
                double s1=state[ch*2],s2=state[ch*2+1];
                const double b0=c[0],a1=c[3],a2=c[4],first=b0*a1,second=b0*a2;
                for(size_t i=0;i<32;++i){
                    const double x=ch?input[i].r:input[i].l;double y;
                    if(quiet){
                        y=std::abs(s1)>=1e-37?s1:0;
                        const double tail=std::abs(s2)>=1e-37?s2:0;
                        s1=y==0?tail:tail-a1*y;s2=y==0?0:-a2*y;
                    }else{
                        const double previous=s1;y=b0*x+s1;
                        s1=((c[1]*x-first*x)+s2)-a1*previous;
                        s2=(c[2]*x-second*x)-a2*previous;
                    }
                    if(ch)output[i].r=static_cast<float>(y);else output[i].l=static_cast<float>(y);
                }
                state[ch*2]=static_cast<float>(s1);state[ch*2+1]=static_cast<float>(s2);
            }
        }
    };
struct Pitch {
    std::span<Stereo> ring;std::array<uint64_t,64> valid{};unsigned validCount{};unsigned writer{},reader{2304},second{},windowBlocks{},change{117};
    float fraction{},window{},fade{},direct{1};bool down{};Biquad filter;
    Stereo at(unsigned index)const noexcept {return validCount==4096||(valid[index/64]&(uint64_t{1}<<(index%64)))?ring[index]:Stereo{};}
    unsigned wrap(int value)const noexcept{return static_cast<unsigned>(value+8192)%4096;}
    void restart(bool direction){
        writer=second=windowBlocks=0;reader=4096-(direction?640:1792);
        change=direction?48:117;fraction=window=fade=0;direct=1;down=direction;filter.state={};
    }
    Block read(unsigned& cursor,float& phase,float increment){
        Block result{};
        for(unsigned i=0;i<32;++i){
            if(down){result[i]=at(wrap(static_cast<int>(cursor)-1))*phase+at(cursor)*(1-phase);phase+=increment;if(phase<1)cursor=(cursor+1)%4096;else phase-=1;}
            else{result[i]=at(cursor)*(1-phase)+at((cursor+1)%4096)*phase;phase+=increment;cursor=(cursor+1)%4096;while(phase>=1){phase-=1;cursor=(cursor+1)%4096;}}
        }
        return result;
    }
    void process(const Block& input,Block& output,unsigned raw){
        for(auto x:input){ring[writer]=x;if(validCount<4096){const auto mask=uint64_t{1}<<(writer%64);if(!(valid[writer/64]&mask)){valid[writer/64]|=mask;++validCount;}}writer=(writer+1)%4096;}
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

struct Return {
    std::array<std::span<Stereo>,4> lines;
    std::array<float,4> weights{},targets{},steps{},readGain{};unsigned writer{},age{},blocks{},lastTime{};
    float sendGate{1};bool enabled{true};
    float activation{},activationTarget{-1},activationStep{};unsigned activationBlocks{};
    void restart(){
        weights=targets=steps=readGain={};writer=age=blocks=lastTime=activationBlocks=0;
        sendGate=1;enabled=true;activation=activationStep=0;activationTarget=-1;
    }
    void controls(unsigned time,unsigned main,bool active){
        enabled=active;
        if(time!=lastTime){
            lastTime=time;targets={};const float position=std::clamp((static_cast<int>(time)-3)/62.25f,0.f,4.f);const auto upper=std::min(3u,static_cast<unsigned>(position));
            if(upper>0)targets[upper-1]=upper+1-position;targets[upper]=position-upper;if(position==4)targets[3]=1;
            for(unsigned i=0;i<4;++i)steps[i]=(targets[i]-weights[i])*.00625f;blocks=5;
        }
        const float target=main<4?0.f:main<=8?main*.2f-.8f:1.f;
        if(target!=activationTarget){activationTarget=target;activationStep=(target-activation)*.00625f;activationBlocks=5;}
    }
    Stereo process(Stereo input){
        Stereo sum{};activation+=activationStep;sendGate=std::clamp(sendGate+(enabled?.00625f:-.00625f),0.f,1.f);
        for(unsigned i=0;i<4;++i){
            weights[i]+=steps[i];const unsigned delay=(i+1)*6000;readGain[i]=std::clamp(readGain[i]+((age/32*32)>=delay?.00625f:-.00625f),0.f,1.f);const auto tap=age>=delay?lines[i][(writer+24004-delay)%24004]*readGain[i]:Stereo{};
            sum=sum+tap;const auto feed=(((input*weights[i])*activation)*sendGate)*.7079457640647888f;lines[i][writer]=feed+tap*.75f;
        }
        writer=(writer+1)%24004;age=std::min(age+1,24032u);return sum*.7f;
    }
    void endBlock(){
        if(blocks&&!--blocks){weights=targets;steps={};}
        if(activationBlocks&&!--activationBlocks){activation=activationTarget;activationStep=0;}
    }
};

    Controls controls;
    int lastDesired{-2},pendingRestart{-1};unsigned historyWritten{};
    bool down{},first{true},descending{},active{true},initialized{},dryRestart{true},dryWarming{true};unsigned currentMain{128},writer{},quiet{},activityCount{},dryBlocks{},rawWriter{},rawAge{},primaryAge{},privateAge{};
    float rawMix{1},rawStep{},primaryGain{},privateGain{},commonWet{},commonStep{.00625f};bool rawArmed{};
    float dryTarget{1},dryStep{},activityAverage{},inputGate{1},inputGain{1},dryGain{1},outputGain{},average{},held{},phase{},velocity{},acceleration{},targetVelocity{};
    double delay{};
    Biquad inputFilter,high,low,post;Pitch pitch;
    std::span<Stereo> history,rawHistory;Return echoes;
    unsigned rawWritten{};bool prepared{},storageActive{},rawActive{};
    void configure() noexcept;
    void resetState(bool preserveRaw) noexcept;
    unsigned targetDelay(unsigned raw) const noexcept;
    float targetGain(float loopGain) const noexcept;
    void restartPrivate(bool direction) noexcept;
    void updateDelay(unsigned target) noexcept;
};
}
