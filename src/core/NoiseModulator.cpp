#include "rmx/NoiseModulator.h"

namespace rmx {
// Compile this translation unit with FP contraction disabled. Both the live
// Engine and offline control probes call these same operation-ordered functions.
const std::array<float,32>& NoiseModulator::sidechain(int raw,const std::array<float,32>& detector,float target) noexcept {
        raw=std::clamp(raw,0,255);
        if(!initialized){smoothed=raw;initialized=true;}
        for(unsigned i=0;i<32;++i){
            const int desired=std::max(0,raw-3);
            smoothed+=smoothed<desired?1:smoothed>desired?-1:0;
            smoothed=std::clamp(smoothed,0,252);
        }
        if(target!=thresholdTarget){
            thresholdStep=(target-thresholdTarget)*.00625f;
            threshold=thresholdTarget;thresholdTarget=target;thresholdBlocks=5;
        }
        const float amount=smoothed*(1.f/252);
        for(unsigned i=0;i<32;++i){
            threshold+=thresholdStep;
            const float boundary=threshold*.41356974840164185f;
            envelope=envelope<detector[i]?(detector[i]-envelope)+envelope:envelope*.9996678233146667f;
            gate=boundary<envelope?(gate+.0024430807679891586f)-gate*.0024430807679891586f:gate*.9996205568313599f;
            output[i]=gate*amount;
        }
        if(thresholdBlocks&&!--thresholdBlocks){threshold=target;thresholdStep=0;}
        if(envelope<1e-10f)envelope=0;
        if(gate<1e-10f)gate=0;
        return output;
    }
const std::array<float,32>& NoiseModulator::generate(int raw,int wave,bool resonance,const RandomSource* source) noexcept {
        raw=std::clamp(raw,0,255);
        if(!initialized){smoothed=raw;initialized=true;}
        std::array<float,32> increments{};
        const int target=std::max(0,raw-3);
        for(auto& increment:increments){
            smoothed+=smoothed<target?1:smoothed>target?-1:0;
            smoothed=std::clamp(smoothed,0,252);
            period=9600.f+((960.f-9600.f)*(1.f/252))*smoothed;
            depth=smoothed<40?smoothed*.025f:1.f;
            increment=1.f/period;
        }
        if(resonance||wave>3){output.fill(0);return output;}
        if(wave==3){
            for(unsigned half=0;half<2;++half){
                if(counter>=static_cast<unsigned>(period)){
                    if(source)randomTarget=source->next(source->state);
                    else{
                        random^=random<<13;random^=random>>17;random^=random<<5;
                        randomTarget=static_cast<int32_t>(random)*(1.f/2147483648.f);
                    }
                    ++randomDraws;
                    randomStep=(randomTarget-phase)*(1.f/128);remaining=8;counter=0;
                }
                for(unsigned i=0;i<16;++i){phase+=randomStep;output[half*16+i]=phase*depth;}
                if(remaining&&!--remaining){phase=randomTarget;randomStep=0;}
                counter+=16;
            }
            return output;
        }
        for(unsigned i=0;i<32;++i){
            if(wave==2){
                phase=std::clamp(phase+(counter>static_cast<unsigned>(period*.5f)?-1.f/64:1.f/64),-1.f,1.f);
                if(++counter>static_cast<unsigned>(period))counter=0;
            }else{
                phase+=descending?-(wave==0?4.f:2.f)*increments[i]:wave==0?4.f*increments[i]:1.f/64;
                if(phase>1){phase=2-phase;descending=true;}
                if(phase<-1){phase=-2-phase;descending=false;}
            }
            output[i]=phase*depth;
        }
        return output;
    }
}
