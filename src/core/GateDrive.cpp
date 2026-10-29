#include "rmx/CalibratedGateDrive.h"

namespace rmx {
void CalibratedGateDrive::reset() noexcept { *this=CalibratedGateDrive{}; prepare(); }

void CalibratedGateDrive::Biquad::process(std::span<const Stereo,32> input,std::span<Stereo,32> output) noexcept {
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

void CalibratedGateDrive::Fourth::configure(std::array<float,5> c) noexcept {first.c=second.c=c;}

void CalibratedGateDrive::Fourth::process(std::span<const Stereo,32> input,std::span<Stereo,32> output) noexcept {std::array<Stereo,32> temp{};first.process(input,temp);second.process(temp,output);}

CalibratedGateDrive::Level::Level() noexcept {history.fill(.05f);}

void CalibratedGateDrive::Level::update(std::span<const Stereo,32> band) noexcept {
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

void CalibratedGateDrive::Band::updateThreshold() noexcept {
            if(level.target!=thresholdTarget){thresholdStep=(level.target-thresholdTarget)*.00625f;threshold=thresholdTarget;thresholdTarget=level.target;thresholdBlocks=5;}
        }

void CalibratedGateDrive::Band::finishThreshold() noexcept {if(thresholdBlocks&&!--thresholdBlocks){threshold=level.target;thresholdStep=0;}}

void CalibratedGateDrive::initializeBands() noexcept {
        for(size_t i=0;i<bands.size();++i){
            auto& b=bands[i];const auto level=b.level;const auto post=b.post.c,extra=b.lowExtra.c;const auto thresholdStep=b.thresholdStep;
            // The original resets the level and countdown but retains this
            // increment across mode initialization, including interrupted ramps.
            b=Band{};b.level=level;b.post.c=post;b.lowExtra.c=extra;b.thresholdStep=thresholdStep;b.raw=static_cast<int>(controls[i]);
            b.side=b.raw>148?1:-1;b.neutral=b.raw>=108&&b.raw<=148;b.dry=b.dryTarget=b.neutral?1.f:0.f;
        }
    }

void CalibratedGateDrive::prepare() noexcept {
        lpLow.configure({.00033661825000308454f,.0006732365000061691f,.00033661825000308454f,-1.9474375247955322f,.9487839937210083f});
        hpLow.configure({.9740554094314575f,-1.948110818862915f,.9740554094314575f,-1.9474375247955322f,.9487839937210083f});
        lpHigh.configure({.06392205506563187f,.12784411013126373f,.06392205506563187f,-1.1685705184936523f,.4242587685585022f});
        hpHigh.configure({.6482073068618774f,-1.2964146137237549f,.6482073068618774f,-1.1685705184936523f,.4242587685585022f});
        bands[0].post.c={.3323010206222534f,.6646020412445068f,.3323010206222534f,.15346477925777435f,.17573928833007812f};
        bands[1].post.c={.15505102276802063f,.31010204553604126f,.15505102276802063f,-.6202040910720825f,.24040821194648743f};
        bands[2].post.c={.006449637934565544f,.012899275869131088f,.006449637934565544f,-1.760317325592041f,.7861158847808838f};
        bands[2].lowExtra.c=lpLow.first.c;
    }

void CalibratedGateDrive::processBand(unsigned index,std::span<const Stereo,32> input,std::span<Stereo,32> output) noexcept {
        auto& b=bands[index];bool changeSide=false;
        if(b.raw<static_cast<int>(controls[index]))++b.raw;
        else if(b.raw>static_cast<int>(controls[index]))--b.raw;
        if(b.side<0&&b.raw>=148){b.raw=147;changeSide=true;}
        if(b.side>0&&b.raw<=107){b.raw=108;changeSide=true;}
        const bool neutral=b.side<0?b.raw>107:b.raw<148;
        if(neutral!=b.neutral){b.neutral=neutral;b.dryTarget=neutral?1.f:0.f;b.dryStep=(b.dryTarget-b.dry)*.00625f;b.fade=5;}
        b.updateThreshold();
        std::array<Stereo,32> effect{};
        if(b.side>0){
            float gain,out,clip;
            if(b.raw>=148){
                float amount=(b.raw-148)*.009345794096589088f;
                if(index==2){gain=amount*4.011872291564941f+1;out=b.raw<184?1.5437999963760376f-b.raw*.0032999999821186066f:1.1486999988555908f-b.raw*.0010999999940395355f;clip=(1-amount*amount)*.11999999731779099f+.47999998927116394f;}
                else{gain=amount*9.377830505371094f+1.5848932266235352f;out=index==1?(b.raw<=210?b.raw*-.005900000222027302f+1.627500057220459f:b.raw*-.0013000000035390258f+.6700999736785889f):(b.raw<=200?b.raw*-.008700000122189522f+2.2548000812530518f:b.raw*-.0005000000237487257f+.6014999747276306f);clip=.47999998927116394f;}
            }else{gain=index==2?1:1.5848932266235352f;out=index==2?1.055400013923645f:(index==1?.7542999982833862f:.967199981212616f);clip=index==2?.6000000238418579f:.47999998927116394f;}
            if(index==2)b.lowExtra.process(input,effect);else std::copy(input.begin(),input.end(),effect.begin());
            float gainStep=(gain-b.inputGain)*.03125f,outStep=(out-b.outputGain)*.03125f;
            for(auto& x:effect){b.inputGain+=gainStep;b.threshold+=b.thresholdStep;float ceiling=b.threshold*clip;x.l=std::max(-ceiling,std::min(ceiling,x.l*b.inputGain));x.r=std::max(-ceiling,std::min(ceiling,x.r*b.inputGain));}
            b.post.process(effect,effect);
            for(auto& x:effect){b.outputGain+=outStep;b.mix+=b.mixStep;x.l=(x.l*b.outputGain)*b.mix;x.r=(x.r*b.outputGain)*b.mix;}
            b.inputGain=gain;b.outputGain=out;
        }else{
            float thresholdFactor,decay,attack=1,amplitude=1;
            if(b.raw>107){thresholdFactor=index==2?.23999999463558197f:.33000001311302185f;decay=.9999169111251831f;attack=index==2?.0012215403839945793f:1;}
            else{
                float amount=(107-b.raw)*.009345794096589088f;float inverse=1-amount;float curve=1-inverse*inverse;
                if(index==2){thresholdFactor=curve*.36000001430511475f+.23999999463558197f;decay=(1-amount*amount)*.0027129214722663164f+.9971208572387695f;attack=.0024430807679891586f;}
                else if(index==1){thresholdFactor=curve*.14000000059604645f+.23999999463558197f;decay=(1-amount*amount)*.0006561679183505476f+.9991776347160339f;}
                else{thresholdFactor=curve*.23250000178813934f+.33000001311302185f;decay=(1-amount*amount)*.0006561679183505476f+.9991776347160339f;}
            }
            float amplitudeStep=(1-b.gateOutput)*.03125f;
            for(size_t i=0;i<32;++i){
                b.threshold+=b.thresholdStep;float peak=std::max(std::abs(input[i].l),std::abs(input[i].r));
                const float detectorDecay=b.raw>107?.999833881855011f:.9996678233146667f;
                b.envelope=b.envelope<peak?(peak-b.envelope)+b.envelope:b.envelope*detectorDecay;
                b.gate=b.threshold*thresholdFactor<b.envelope?(b.gate+attack)-b.gate*attack:b.gate*decay;
                b.mix+=b.mixStep;b.gateOutput+=amplitudeStep;
                effect[i]={((input[i].l*b.gate)*b.mix)*b.gateOutput,((input[i].r*b.gate)*b.mix)*b.gateOutput};
            }
            b.gateOutput=amplitude;
            if(b.envelope<1e-10f)b.envelope=0;if(b.gate<1e-10f)b.gate=0;
        }
        b.finishThreshold();if(b.mix>1-.00625f){b.mix=1;b.mixStep=0;}
        for(size_t i=0;i<32;++i){b.dry+=b.dryStep;output[i]={effect[i].l*(1-b.dry)+input[i].l*b.dry,effect[i].r*(1-b.dry)+input[i].r*b.dry};}
        if(b.fade&&!--b.fade){b.dry=b.dryTarget;b.dryStep=0;}
        if(changeSide){b.side=-b.side;b.gate=1;b.envelope=0;}
    }

void CalibratedGateDrive::process(std::span<const Stereo,32> input,std::span<Stereo,32> output) noexcept {
        std::array<Stereo,32> low{},middle{},high{},above{};
        lpLow.process(input,low);hpLow.process(input,above);lpHigh.process(above,middle);hpHigh.process(input,high);
        bands[0].level.update(high);bands[1].level.update(middle);bands[2].level.update(low);
        if(selected){if(initializing){initializeBands();initializing=false;}processBand(0,high,high);processBand(1,middle,middle);processBand(2,low,low);}
        if(enabled!=selected){step=-.00625f;phase=1;}else if(phase==2)step=.00625f;
        for(size_t i=0;i<32;++i){
            const Stereo sum=selected?(high[i]+middle[i])+low[i]:input[i];
            master+=step;
            output[i]={sum.l*master+input[i].l*(1-master),sum.r*master+input[i].r*(1-master)};
        }
        if(master>1-.00625f){master=1;step=0;phase=0;}
        if(master<.00625f){master=step=0;selected=enabled;phase=2;initializing=selected;}
    }
}
