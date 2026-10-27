#pragma once
#include "rmx/drums/Kick.h"
#include "rmx/drums/Snare.h"
#include "rmx/drums/Clap.h"
#include "rmx/drums/Hat.h"
#include "rmx/Scene.h"
#include "rmx/CalibratedReverbUp.h"
#include "rmx/CalibratedReverbDown.h"
#include <stdexcept>

// Research adapter: one input/output FIFO for generated drums and Scene audio.
// Static factory controls only; this is not the live Engine.
class SharedDrumFX {
public:
    SharedDrumFX(int type,int route,int main,int amount,int cutoff,bool enabled,unsigned level,unsigned pitch):
        type(type),route(route),main(main),amount(amount),cutoff(cutoff),enabled(enabled) {
        kick.setControls(level,pitch);snare.setControls(level,pitch);clap.setControls(level,pitch);hat.setControls(level,pitch);
        scene.prepare(48000);rmx::SceneSettings settings;settings.type=type;scene.configure(settings);
        up.prepare(32);down.prepare(32);up.setControls({main,amount,cutoff,enabled});down.setControls({main,amount,cutoff,enabled});
    }
    void trigger(unsigned pad) noexcept {
        switch(pad){case 0:kick.trigger();break;case 1:snare.trigger();break;case 2:clap.trigger();break;case 3:hat.trigger();break;}
    }
    void process(std::span<const rmx::Stereo> input,std::span<rmx::Stereo> output) {
        kick.beginProcessing();snare.beginProcessing();clap.beginProcessing();hat.beginProcessing();
        std::copy(input.begin(),input.end(),output.begin());size_t read=0,written=0;
        while(read<input.size()){
            const auto take=std::min(32-received,input.size()-read);
            std::copy_n(input.begin()+static_cast<std::ptrdiff_t>(read),take,collected.begin()+static_cast<std::ptrdiff_t>(received));
            received+=take;read+=take;
            const auto emit=std::min(available,input.size()-written);
            std::copy_n(pending.begin()+static_cast<std::ptrdiff_t>(head),emit,output.begin()+static_cast<std::ptrdiff_t>(written));
            written+=emit;available-=emit;head+=emit;
            if(received==32){generate();received=0;available=32;head=0;}
        }
    }
private:
    void generate() {
        std::array<rmx::Stereo,32> drums{},selected{},generated{},unselected{};std::array<float,32> scratch{};
        auto add=[&](auto& voice){voice.generateBlock(scratch);for(size_t i=0;i<32;++i)drums[i]=drums[i]+rmx::Stereo{scratch[i],scratch[i]};};
        add(kick);add(snare);add(clap);add(hat);
        for(size_t i=0;i<32;++i){
            const bool inputSelected=route==0||route==2,padSelected=route==1||route==2;
            float fade=1;if(age<160){startup+=.00625f;fade=startup;}++age;
            const auto raw=collected[i];const rmx::Stereo routed{(raw.l*fade)*fade,(raw.r*fade)*fade};
            selected[i]=inputSelected?raw:rmx::Stereo{};generated[i]=padSelected?drums[i]:rmx::Stereo{};
            unselected[i]=(inputSelected?rmx::Stereo{}:routed)+(padSelected?rmx::Stereo{}:drums[i]);
            if(type!=4&&type!=9){
                const auto send=(inputSelected?routed:rmx::Stereo{})+generated[i];
                const auto frame=age-1;const bool first=enabled&&frame<32;
                if(enabled&&frame>=32&&frame<192)effectStartup=std::min(1.f,effectStartup+.00625f);
                if(frame>=192)effectStartup=1;
                const auto steady=scene.process(send,main/255.f,amount*7.f/255,cutoff/255.f,enabled?1.f:0.f,120,static_cast<double>(age)/24000,0,
                                               enabled?effectStartup:1,first);
                rmx::Stereo result=steady;
                if(enabled){
                    if(first){effectMix+=.00625f;result=send;}
                    else if(frame<224){
                        if(frame==32){
                            const float position=std::clamp(1.f-(main-3)*(type==7?1.f/126:1.f/63),0.f,1.f);
                            directTarget=(type==0||type==1)?1.f:position*position;
                            directStep=(directTarget-direct)*.00625f;effectStep=(1-effectMix)*.00625f;
                        }
                        if(frame==64)directStep=(directTarget-direct)*.00625f;
                        direct+=directStep;if(frame<192)effectMix+=effectStep;
                        result=send*direct+(steady-send*directTarget)*effectMix;
                        if(frame==191)effectMix=1;
                        if(frame==223)direct=directTarget;
                    }
                }
                pending[i]=unselected[i]+result;
            }
        }
        if(type==4||type==9){
            const bool ok=type==4?up.processGeneratedBlock(selected,generated,pending):down.processGeneratedBlock(selected,generated,pending);
            if(!ok)throw std::runtime_error("Shared reverb block rejected");
            for(size_t i=0;i<32;++i)pending[i]=pending[i]+unselected[i];
        }
    }
    rmx::drums::Kick kick;rmx::drums::Snare snare;rmx::drums::Clap clap;rmx::drums::Hat hat;
    rmx::SceneProcessor scene;rmx::CalibratedReverbUp up;rmx::CalibratedReverbDown down;
    int type{},route{},main{},amount{},cutoff{};bool enabled{};
    std::array<rmx::Stereo,32> collected{},pending{};size_t received{},available{},head{},age{};float startup{};
    float effectMix{},effectStep{},direct{1},directTarget{1},directStep{};
    float effectStartup{};
};
