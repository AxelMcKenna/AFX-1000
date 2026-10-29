#pragma once
#include "rmx/Dsp.h"
#include "rmx/CalibratedTransRoll.h"
#include "rmx/CutFilterCoefficients.h"
#include <array>
#include <bit>
#include <cstdint>
#include <limits>

namespace rmx {
// Default48k/manual120BPM Cut/Add. See research/audio/cut-add.md for qualification.
struct CalibratedCutAdd {
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
    struct Fourth {
        Biquad first,second;
        void configure(std::array<float,5> c){first.c=second.c=c;}
        void process(std::span<const Stereo,32> input,std::span<Stereo,32> output){std::array<Stereo,32> temp{};first.process(input,temp);second.process(temp,output);}
    };
    Fourth lpLow,hpLow,lpHigh,hpHigh;
    std::array<unsigned,3> controls{128,128,128};
    float master{1},step{};unsigned phase{};bool selected{},enabled{},initializing{};
    Biquad equalizer;std::array<Biquad,3> low,high,detector;
    struct ManualFilter {
        std::array<std::array<float,4>,2> state{};
        Stereo process(Stereo input,const std::array<float,5>& c){
            Stereo result;
            for(unsigned ch=0;ch<2;++ch){auto& s=state[ch];const float x=ch?input.r:input.l;
                const float y=((c[2]*s[1]-c[3]*s[2])-c[4]*s[3])+(c[0]*x+c[1]*s[0]);
                s[1]=s[0];s[0]=x;s[3]=s[2];s[2]=y;if(ch)result.r=y;else result.l=y;
            }
            return result;
        }
    };
    std::array<ManualFilter,2> manual{};std::array<float,2> manualGain{};
    std::array<int,3> raw{128,128,128};float lowGain{1};bool configured{};
    std::array<uint32_t,2> integrators{};std::array<uint32_t,4> comb{};
    float envelope{},topFast{},longEnvelope{},topLong{},bottomLong{},gainBottom{},gainSmooth{};uint16_t maskCount{};
    CalibratedTransRoll* pool{};bool storageActive{};
    std::array<std::array<float,7>,3> addWeights{};unsigned addWriter{},addCount{};float addReady{},addFade{};
    void resetAdd(){
        addWeights={};addWriter=addCount=0;addReady=addFade=0;
        for(auto* f:{&hpLow,&lpHigh,&hpHigh}){f->first.state={};f->second.state={};}
    }
    void processAdd(std::span<const Stereo,32> residual,std::span<const Stereo,32> kick,std::span<Stereo,32> result){
        std::array<Stereo,32> middle{},high{},above{};
        hpLow.process(residual,above);lpHigh.process(above,middle);hpHigh.process(residual,high);
        const std::array<std::span<const Stereo,32>,3> sources{high,middle,kick};
        std::array<std::array<float,7>,3> target{},delta{};
        for(unsigned band=0;band<3;++band){
            const float amount=std::min(124.f,static_cast<float>(std::max(0,raw[band]-131)));
            const float fix=amount>62?amount*-.006000000052154064f+1.378000020980835f:1.f;
            const float a=amount*.024193547666072845f;
            target[band]={a-2,a-1,a-2,a,a-2,a-1,a-2};
            for(unsigned tap=0;tap<7;++tap){target[band][tap]=std::clamp(target[band][tap],0.f,1.f);if(amount>62)target[band][tap]*=fix;delta[band][tap]=(target[band][tap]-addWeights[band][tap])*.03125f;}
        }
        const bool ready=addCount>=48000;
        if(addCount<=0xfffff){if(!ready)addReady=0;addCount+=64;}
        for(unsigned i=0;i<32;++i){
            for(unsigned band=0;band<3;++band)for(unsigned tap=0;tap<7;++tap)addWeights[band][tap]+=delta[band][tap];
            addReady=std::clamp(addReady+(ready?.00625f:0),0.f,1.f);addFade=std::min(1.f,addFade+.00625f);
            const float gain=addReady*(addFade*(ready?1.f:0.f));std::array<Stereo,3> bands{};
            for(unsigned band=0;band<3;++band){
                std::array<Stereo,7> taps{};
                for(unsigned tap=0;tap<7;++tap)taps[tap]=pool->memory(band*196608+(addWriter+196608-3000*(tap+1)+i)%196608)*addWeights[band][tap];
                const Stereo first=(taps[0]+taps[1])*gain,second=(taps[2]+taps[3])*gain,third=((taps[4]+taps[5])+taps[6])*gain;
                bands[band]=third+(second+first);
            }
            result[i]={((bands[2].l*1.5f+(bands[0].l+bands[1].l))*.7699999809265137f),((bands[2].r*1.5f+(bands[0].r+bands[1].r))*.7699999809265137f)};
        }
        addWeights=target;
        for(unsigned band=0;band<3;++band)for(unsigned i=0;i<32;++i)pool->memory(band*196608+addWriter+i)=sources[band][i];
        addWriter=(addWriter+32)%196608;
    }
    Fourth dryHigh,dryMidHigh,dryMidLow,dryLow;
    struct DryGain {float value{},target{},step{};unsigned blocks{};};std::array<DryGain,3> dryGains{};
    void bypassBlock(std::span<const Stereo,32> input,std::span<Stereo,32> output){
        std::array<Stereo,32> high{},middle{},low{},below{};
        dryHigh.process(input,high);dryMidHigh.process(input,below);dryMidLow.process(below,middle);dryLow.process(input,low);
        for(unsigned band=0;band<3;++band){auto& g=dryGains[band];const auto raw=controls[band];const float target=raw<=1?0.f:raw<=123?1-(124-raw)*.008130080997943878f:1.f;if(target!=g.target){g.target=target;g.step=(target-g.value)*.00625f;g.blocks=5;}}
        for(unsigned i=0;i<32;++i){for(auto& g:dryGains)g.value+=g.step;output[i]={((high[i].l*dryGains[0].value+middle[i].l*dryGains[1].value)+low[i].l*dryGains[2].value),((high[i].r*dryGains[0].value+middle[i].r*dryGains[1].value)+low[i].r*dryGains[2].value)};}
        for(auto& g:dryGains)if(g.blocks&&!--g.blocks){g.value=g.target;g.step=0;}
    }
    void detectorBlock(std::span<const Stereo,32> input,std::span<float,32> gain){
        std::array<Stereo,32> bass{};
        if(configured){detector[0].process(input,bass);detector[1].process(bass,bass);detector[2].process(bass,bass);}
        for(auto x:bass){const float scaled=((x.l+x.r)*.5f)*32768.f;const auto value=scaled>=-2147483648.f&&scaled<2147483648.f?static_cast<int32_t>(scaled):std::numeric_limits<int32_t>::min();integrators[0]+=static_cast<uint32_t>(value);integrators[1]+=integrators[0];}
        const uint32_t difference=integrators[1]-comb[1]-comb[3];const auto signedDifference=std::bit_cast<int32_t>(difference);
        const int32_t quantized=static_cast<int32_t>(static_cast<float>(signedDifference)*(1.f/4096));
        const auto q=std::bit_cast<int16_t>(static_cast<uint16_t>(quantized));const float value=static_cast<float>(q)*(1.f/32768);
        const auto last=comb[0],previous=comb[2];comb[3]=previous;comb[2]=integrators[1]-comb[1];comb[1]=last;comb[0]=integrators[1];
        const float differenceEnvelope=std::max(0.f,std::abs(value)-envelope);
        envelope=(differenceEnvelope*.4865829050540924f+envelope)-envelope*.0033278469927608967f;
        const float fast=envelope*1.0068390369415283f;
        topFast=topFast-fast>.00013333333481568843f?topFast-.00013333333481568843f:fast;
        longEnvelope=longEnvelope*.9958199262619019f+fast*.004180132877081633f;
        topLong=topLong-longEnvelope>.00013333333481568843f?topLong-.00013333333481568843f:longEnvelope;
        bottomLong=longEnvelope-bottomLong>.00026666666963137686f?bottomLong+.00026666666963137686f:longEnvelope;
        const float lower=0.f*topFast+topLong,upper=.1f*topFast+topLong;
        float target=1;
        if(fast>lower){if(fast>upper)++maskCount;if(maskCount>0&&maskCount<93)target=std::clamp((1.f/(fast*(.65f*10.f)+.00001f))*bottomLong,0.f,1.f);}
        else maskCount=0;
        gainBottom=target-gainBottom>.006666666828095913f?gainBottom+.006666666828095913f:target;
        for(auto& g:gain){gainSmooth=gainSmooth*.9934762716293335f+gainBottom*.006523669231683016f;g=gainSmooth;}
    }
    void prepare(CalibratedTransRoll& storage) noexcept {pool=&storage;reset();}
    void reset() noexcept {auto* storage=pool;*this=CalibratedCutAdd{};pool=storage;configure();}
    void setStorageActive(bool active) noexcept {
        if(active==storageActive)return;
        storageActive=active;
        if(!active){selected=initializing=enabled=false;master=1;step=0;phase=0;}
    }
    void setControls(std::array<unsigned,3> lowMidHigh,bool active) noexcept {
        for(unsigned i=0;i<3;++i)controls[2-i]=std::min(lowMidHigh[i],255u);
        enabled=active&&storageActive;
    }
    void configure() noexcept {lpLow.configure({.00033661825000308454f,.0006732365000061691f,.00033661825000308454f,-1.9474375247955322f,.9487839937210083f});
hpLow.configure({.9740554094314575f,-1.948110818862915f,.9740554094314575f,-1.9474375247955322f,.9487839937210083f});
lpHigh.configure({.06392205506563187f,.12784411013126373f,.06392205506563187f,-1.1685705184936523f,.4242587685585022f});
hpHigh.configure({.6482073068618774f,-1.2964146137237549f,.6482073068618774f,-1.1685705184936523f,.4242587685585022f});dryHigh.configure(hpHigh.first.c);dryMidHigh.configure(lpHigh.first.c);dryMidLow.configure(hpLow.first.c);dryLow.configure(lpLow.first.c);low[0].c={0.00037130399141460657f,0.0007426079828292131f,0.00037130399141460657f,-1.9254510402679443f,0.9269359707832336f};high[0].c={0.9630966782569885f,-1.9261929988861084f,0.9630966782569885f,-1.9254510402679443f,0.9269359707832336f};low[1].c={0.0003749745083041489f,0.0007499490748159587f,0.0003749745083041489f,-1.9444849491119385f,0.9459847211837769f};high[1].c={0.9726173877716064f,-1.945235013961792f,0.9726173877716064f,-1.9444849491119385f,0.9459847211837769f};low[2].c={0.0003815068048425019f,0.0007630136096850038f,0.0003815068048425019f,-1.9783589839935303f,0.9798846244812012f};high[2].c={0.9895607829093933f,-1.9791220426559448f,0.9895607829093933f,-1.9783589839935303f,0.9798846244812012f};for(unsigned i=0;i<3;++i)detector[i].c=low[i].c;configured=true;equalizer.c={.9977108240127563f,-1.9834699630737305f,.9865443706512451f,-1.9834699630737305f,.984255313873291f};}

    void process(std::span<const Stereo,32> input,std::span<Stereo,32> output) noexcept;
};
}
