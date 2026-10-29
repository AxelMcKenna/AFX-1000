#pragma once
#include "IsolateNeutral.h"
#include <vector>

namespace rmx::research {
// Active Trans/Roll identification model; not qualified for live delivery.
struct TransRoll : IsolateNeutral {
    struct TransBand {
        int raw{128},depth{},rollDepth{},attackAge{},thresholdSamples{};
        float threshold{.05f},thresholdTarget{.05f},thresholdStep{},envelope{};
        bool start{};int compensation{},maskClock{},stage{},stageAge{},gainCountdown{},maskCountdown{};
        float duty{1},gain{1},gainTarget{1},gainStep{},mask{1},maskStep{};
        int mark{1},previousMark{1},gridPhase{},gridTicks{};
        struct Voice {int reader{},weightCountdown{};bool returning{};float ready{},readyStep{.00625f},weight{},weightTarget{},weightStep{},readyLast{};};
        std::array<Voice,3> voices{};std::array<int,3> gridCounts{16,8,4};
        bool rollStart{},recording{};int rawReader{},writer{},directCountdown{};
        float direct{1},directTarget{1},directStep{};
    };
    std::array<TransBand,3> trans{};
    std::array<std::vector<Stereo>,3> history{},capture{};int rawWriter{};
    double timeline{},previousGrid{};int elapsed{};
    void prepare(){IsolateNeutral::prepare();for(auto& h:history)h.resize(196608);for(auto& h:capture)h.resize(196608);}
    void updateRollMix(TransBand& b){
        std::array<float,3> weights{};float direct=0;unsigned voice=0;
        if(b.rollDepth<=10)direct=1;
        else if(b.rollDepth<=30){weights[0]=b.rollDepth*.05f-.5f;direct=b.rollDepth<=20?1:b.rollDepth*-.1f+3;}
        else if(b.rollDepth<=50)weights[0]=1;
        else if(b.rollDepth<=100){weights[1]=1;voice=1;}
        else{weights[2]=1;voice=2;}
        if(b.voices[voice].readyLast==0){weights={};direct=1;}
        b.directTarget=direct;for(unsigned i=0;i<3;++i){auto& v=b.voices[i];if(v.weightTarget!=weights[i]){v.weightTarget=weights[i];v.weightStep=(v.weightTarget-v.weight)*.00625f;v.weightCountdown=20;}}
    }
    void processRoll(unsigned index,std::span<Stereo,32> band,bool grid){
        auto& b=trans[index];
        if(b.rollStart){
            b.recording=false;b.direct=b.directTarget=1;b.directStep=0;b.directCountdown=0;
            for(auto& v:b.voices){v.ready=0;v.readyStep=.00625f;v.readyLast=0;v.weight=v.weightTarget=v.weightStep=0;}
            if(b.attackAge<=960){
                b.recording=true;b.gridPhase=elapsed>750?0:1;
                for(unsigned i=0;i<3;++i)b.gridCounts[i]=(16>>i)+(elapsed>750?1:0);
                if(elapsed<=750)b.attackAge=std::min(b.attackAge,elapsed);
                b.rawReader=(rawWriter-b.attackAge-32+196608)%196608;b.writer=0;
                for(auto& v:b.voices){v.reader=0;v.returning=false;}
                b.rollStart=false;
            }
        }
        if(b.start){
            b.compensation=0;b.maskClock=0;
            if(b.attackAge<=960){b.stageAge=0;b.gainCountdown=0;b.stage=0;b.gridTicks=0;b.gridPhase=elapsed>750?-1:0;b.compensation=elapsed>750?-b.attackAge:b.attackAge;b.start=false;}
            else b.mark=1;
        }
        if(b.recording){for(unsigned i=0;i<32;++i)capture[index][b.writer+i]=history[index][(b.rawReader+i)%196608];b.writer+=32;b.rawReader=(b.rawReader+32)%196608;if(b.writer>=196608)b.recording=false;}
        if(grid){
            ++b.gridPhase;for(unsigned i=0;i<3;++i)if(!--b.gridCounts[i]){b.gridCounts[i]=16>>i;b.voices[i].returning=true;}
            if(b.gridPhase>=4){b.gridPhase=0;if(b.gridTicks%4==3)b.maskClock=0;if(++b.gridTicks==16){b.gridTicks=0;b.stage=0;b.stageAge=0;}}
        }
        std::array<Stereo,32> repeated{};
        for(auto& v:b.voices){
            for(unsigned group=0;group<4;++group){
                for(unsigned j=0;j<8;++j){v.ready+=v.readyStep;v.weight+=v.weightStep;const auto x=capture[index][static_cast<size_t>(v.reader+j)];const float gain=v.weight*v.ready;auto& y=repeated[group*8+j];y.l+=gain*x.l;y.r+=gain*x.r;}
                v.reader+=8;if(v.reader>=196448)v.returning=true;
                if(v.returning){v.readyStep=-.00625f;v.readyLast=1;if(v.ready<.00625f){v.reader=0;v.readyStep=.00625f;v.returning=false;v.ready=0;}}
                else if(v.reader>160){v.readyStep=0;v.ready=1;}
                else if(v.ready>1-.00625f){v.readyStep=0;v.ready=1;}
                else v.readyStep=.00625f;
                if(v.weightCountdown&&!--v.weightCountdown){v.weight=v.weightTarget;v.weightStep=0;}
            }
        }
        for(unsigned i=0;i<32;++i){b.direct+=b.directStep;band[i]={band[i].l*b.direct+repeated[i].l,band[i].r*b.direct+repeated[i].r};}
        if(b.directCountdown&&!--b.directCountdown){b.direct=b.directTarget;b.directStep=0;}
    }
    void initializeTrans(){
        for(unsigned i=0;i<3;++i){auto& b=trans[i];b=TransBand{};b.raw=static_cast<int>(controls[i]);b.depth=std::max(0,119-b.raw);b.start=b.depth!=0;b.attackAge=b.depth?-32:0;b.rollDepth=std::max(0,b.raw-136);b.rollStart=b.rollDepth!=0;b.rawReader=rawWriter;}

    }
    void processTrans(unsigned index,std::span<Stereo,32> band,bool grid){
        auto& b=trans[index];if(b.raw<static_cast<int>(controls[index]))++b.raw;else if(b.raw>static_cast<int>(controls[index]))--b.raw;
        const int rollDepth=std::max(0,b.raw-136);if(rollDepth&&b.rollDepth==0)b.rollStart=true;b.rollDepth=rollDepth;
        const auto oldDirect=b.directTarget;updateRollMix(b);if(oldDirect!=b.directTarget){b.directStep=(b.directTarget-b.direct)*.00625f;b.directCountdown=5;}
        const int depth=std::max(0,119-b.raw);if(depth&&b.depth==0)b.start=true;b.depth=depth;
        if(b.attackAge<=999)b.attackAge+=32;
        const float level=bands[index].level.target;
        if(level!=b.thresholdTarget){b.thresholdStep=(level-b.thresholdTarget)*.00625f;b.threshold=b.thresholdTarget;b.thresholdTarget=level;b.thresholdSamples=5;}
        for(auto x:band){
            b.threshold+=b.thresholdStep;float peak=std::max(std::abs(x.l),std::abs(x.r));
            b.envelope=b.envelope<peak?(peak-b.envelope)+b.envelope:b.envelope*.999833881855011f;
            if(b.envelope>b.threshold*(index==2?.7f:.5625f)&&b.attackAge>=960)b.attackAge=0;
            if(b.thresholdSamples&&!--b.thresholdSamples){b.threshold=level;b.thresholdStep=0;}
            if(b.envelope<1e-10f)b.envelope=0;
        }
        // Default pattern: eight equal stages, then a duty-cycle mask.
        if(depth<=10){b.maskClock=0;b.duty=1;}
        else if(depth<=60)b.duty=depth*-.00625f+.625f;
        else if(depth<=100)b.duty=depth*-.003125f+.4375f;
        else b.duty=depth*-.00525f+.65f;
        processRoll(index,band,grid);
        int division=3000;if(b.duty>.125f)division*=b.duty<=.25f?2:b.duty<=.5f?4:8;
        if(b.mark!=b.previousMark){b.previousMark=b.mark;b.maskCountdown=16;b.maskStep=(b.mark?1-b.mask:-b.mask)*.0078125f;}
        for(unsigned group=0;group<4;++group){
            for(unsigned j=0;j<8;++j){auto& x=band[group*8+j];b.gain+=b.gainStep;b.mask+=b.maskStep;x.l=(x.l*b.gain)*b.mask;x.r=(x.r*b.gain)*b.mask;}
            if(b.maskCountdown&&!--b.maskCountdown){b.maskStep=0;b.mask=static_cast<float>(b.previousMark);}
            b.maskClock+=8;b.mark=static_cast<float>(b.maskClock%(division*2))<static_cast<float>(3000*8)*b.duty;
            if(b.maskClock>=24000)b.maskClock=0;
            if(b.gainCountdown&&!--b.gainCountdown){b.gainStep=0;b.gain=b.gainTarget;}
            b.stageAge+=8;if(b.stageAge>=12000-b.compensation){b.stage=(b.stage+1)%8;b.stageAge=0;b.compensation=0;}
        }
        b.gain=std::clamp(b.gain,0.f,1.f);b.mask=std::clamp(b.mask,0.f,1.f);
    }
    void process(std::span<const Stereo,32> input,std::span<Stereo,32> output){
        timeline=timeline+(32.*120)/(48000.*60);const double position=std::fmod(std::fmod(timeline,96.),.0625);const bool grid=position<previousGrid;previousGrid=position;
        if(grid)elapsed=0;else if(elapsed<=20000)elapsed+=32;
        std::array<Stereo,32> low{},middle{},high{},above{};
        lpLow.process(input,low);hpLow.process(input,above);lpHigh.process(above,middle);hpHigh.process(input,high);
        bands[0].level.update(high);bands[1].level.update(middle);bands[2].level.update(low);
        for(unsigned i=0;i<32;++i){history[0][rawWriter+i]=high[i];history[1][rawWriter+i]=middle[i];history[2][rawWriter+i]=low[i];}rawWriter=(rawWriter+32)%196608;
        if(selected){if(initializing){initializeTrans();initializing=false;}processTrans(0,high,grid);processTrans(1,middle,grid);processTrans(2,low,grid);}
        if(enabled!=selected){step=-.00625f;phase=1;}else if(phase==2)step=.00625f;
        for(size_t i=0;i<32;++i){const Stereo sum=selected?(high[i]+middle[i])+low[i]:input[i];master+=step;output[i]={sum.l*master+input[i].l*(1-master),sum.r*master+input[i].r*(1-master)};}
        if(master>1-.00625f){master=1;step=0;phase=0;}
        if(master<.00625f){master=step=0;selected=enabled;phase=2;initializing=selected;}
    }
};
}
