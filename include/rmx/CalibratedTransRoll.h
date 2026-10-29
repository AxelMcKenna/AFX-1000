#pragma once
#include "rmx/Dsp.h"
#include <array>
#include <cassert>

namespace rmx {
// Default48k/120BPM, common32 clock. Qualification: research/audio/trans-roll.md.
struct CalibratedTransRoll {
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
    struct Level {
        std::array<float,24> history{};
        float peak{},held{.05f},smooth{.05f},step{},target{};
        unsigned count{},position{},wait{},ramp{};bool warming{true};
        Level(){history.fill(.05f);}
        void update(std::span<const Stereo,32> band){
            for(auto x:band)peak=std::max(peak,std::max(std::abs(x.l),std::abs(x.r)));
            if(++count==50){history[position]=peak;peak=0;count=0;position=(position+1)%24;warming=false;}
            float recent=history[0];for(size_t i=1;i<23;++i)recent=std::max(recent,history[i]);
            if(warming){held=recent;recent=peak;}
            if(recent>=held){held=smooth=target=recent;step=0;wait=0;}
            else if(held*.75f<=recent){wait=0;target=held;}
            else{if(wait>=1800){step=(recent-held)*.0006666666595265269f;ramp=1500;wait=0;}else ++wait;target=recent;}
            smooth+=step;
            if(ramp&&!--ramp){held=smooth=recent;step=0;wait=0;}
        }
    };
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
    // Six logical rings reuse the twelve mutually exclusive legacy buffers.
    // Only the small remainder and recent-history cache need new SDRAM.
    std::array<std::span<Stereo>,12> borrowed{};
    std::pmr::vector<Stereo> extra,recent;
    std::array<unsigned,3> captureValid{};
    unsigned historyValid{},recentValid{},recentWriter{};int rawWriter{};bool storageActive{};
    std::array<Level,3> levels{};
    std::array<unsigned,3> controls{128,128,128};
    float master{1},step{};unsigned phase{};bool selected{},enabled{},initializing{};
    Stereo& memory(unsigned index) noexcept {
        constexpr unsigned chunk=96004;
        const unsigned part=index/chunk,offset=index%chunk;
        return part<12?borrowed[part][offset]:extra[offset];
    }
    Stereo readHistory(unsigned band,unsigned index) noexcept {
        const unsigned distance=(static_cast<unsigned>(rawWriter)+196608-index)%196608;
        if((distance?distance:196608)>historyValid)return {};
        return memory(band*196608+index);
    }
    Stereo readCapture(unsigned band,unsigned index) noexcept {
        return index<captureValid[band]?memory((band+3)*196608+index):Stereo{};
    }
    void writeCapture(unsigned band,unsigned index,Stereo value) noexcept {
        memory((band+3)*196608+index)=value;captureValid[band]=std::max(captureValid[band],index+1);
    }
    double timeline{},previousGrid{};int elapsed{};
    void prepare(std::array<std::span<Stereo>,12> storage) {
        for([[maybe_unused]] auto s:storage)assert(s.size()==96004);
        borrowed=storage;extra.assign(27600,{});recent.assign(3*1024,{});reset();
    }
    void reset() noexcept {
        trans={};levels={};master=1;step=0;phase=0;selected=enabled=initializing=storageActive=false;
        controls={128,128,128};timeline=previousGrid=0;elapsed=rawWriter=0;
        historyValid=recentValid=recentWriter=0;captureValid={};
        lpLow={};hpLow={};lpHigh={};hpHigh={};
        lpLow.configure({.00033661825000308454f,.0006732365000061691f,.00033661825000308454f,-1.9474375247955322f,.9487839937210083f});
        hpLow.configure({.9740554094314575f,-1.948110818862915f,.9740554094314575f,-1.9474375247955322f,.9487839937210083f});
        lpHigh.configure({.06392205506563187f,.12784411013126373f,.06392205506563187f,-1.1685705184936523f,.4242587685585022f});
        hpHigh.configure({.6482073068618774f,-1.2964146137237549f,.6482073068618774f,-1.1685705184936523f,.4242587685585022f});
    }
    void setStorageActive(bool active) noexcept {
        if(active==storageActive)return;
        storageActive=active;captureValid={};historyValid=0;
        if(active){
            // Only the most recent 20 ms can be rewound at an initial capture.
            // Seed that history from a bounded cache before borrowing the full rings.
            for(unsigned band=0;band<3;++band)for(unsigned i=0;i<recentValid;++i){
                const unsigned index=(static_cast<unsigned>(rawWriter)+196608-recentValid+i)%196608;
                memory(band*196608+index)=recent[band*1024+(recentWriter+1024-recentValid+i)%1024];
            }
            historyValid=recentValid;
        }else{selected=initializing=enabled=false;master=1;step=0;phase=0;}
    }
    void setControls(std::array<unsigned,3> lowMidHigh,bool active) noexcept {
        for(unsigned i=0;i<3;++i)controls[2-i]=std::min(lowMidHigh[i],255u);
        enabled=active&&storageActive;
    }
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
        if(b.recording){for(unsigned i=0;i<32;++i)writeCapture(index,static_cast<unsigned>(b.writer)+i,readHistory(index,(static_cast<unsigned>(b.rawReader)+i)%196608));b.writer+=32;b.rawReader=(b.rawReader+32)%196608;if(b.writer>=196608)b.recording=false;}
        if(grid){
            ++b.gridPhase;for(unsigned i=0;i<3;++i)if(!--b.gridCounts[i]){b.gridCounts[i]=16>>i;b.voices[i].returning=true;}
            if(b.gridPhase>=4){b.gridPhase=0;if(b.gridTicks%4==3)b.maskClock=0;if(++b.gridTicks==16){b.gridTicks=0;b.stage=0;b.stageAge=0;}}
        }
        std::array<Stereo,32> repeated{};
        for(auto& v:b.voices){
            for(unsigned group=0;group<4;++group){
                for(unsigned j=0;j<8;++j){v.ready+=v.readyStep;v.weight+=v.weightStep;const auto x=readCapture(index,static_cast<unsigned>(v.reader)+j);const float gain=v.weight*v.ready;auto& y=repeated[group*8+j];y.l+=gain*x.l;y.r+=gain*x.r;}
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
        const float level=levels[index].target;
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
    void process(std::span<const Stereo,32> input,std::span<Stereo,32> output) noexcept;
};
}
