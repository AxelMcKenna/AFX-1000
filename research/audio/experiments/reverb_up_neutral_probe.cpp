// Independent static factory Up Main128/Sub1-128/48-kHz research model.
#include "rmx/Wav.h"
#include "rmx/Dsp.h"
#include "ReverbUpNeutralCalibration.h"
#include "ReverbUpControlCalibration.h"
#include <iostream>

namespace {
struct Delay {
    std::vector<double> values;size_t head{};
    explicit Delay(size_t size=1):values(size){}
    double read()const noexcept{return values[head];}
    void push(double x)noexcept{values[head]=x;if(++head==values.size())head=0;}
};
struct Filter {
    double b0{1},b1{},b2{},a1{},a2{},s1{},s2{};
    void biquad(double hz,bool high){
        const double w=2*std::numbers::pi*hz/48000,alpha=std::sin(w)/std::sqrt(2.);
        b0=(1+(high?1:-1)*std::cos(w))/2/(1+alpha);b1=(high?-2:2)*b0;b2=b0;
        a1=-2*std::cos(w)/(1+alpha);a2=(1-alpha)/(1+alpha);
    }
    void highpass(double hz){
        const double t=std::tan(std::numbers::pi*hz/48000),p=(1-t)/(1+t);
        b0=(1+p)/2;b1=-b0;b2=0;a1=-p;a2=0;
    }
    double tick(double x)noexcept{const double y=b0*x+s1;s1=b1*x-a1*y+s2;s2=b2*x-a2*y;return y;}
};
struct AllPass {
    Delay delay;
    explicit AllPass(size_t size):delay(size){}
    double tick(double x)noexcept{const double y=delay.read()-.7*x;delay.push(x+.7*y);return y;}
};
double number(const char* input){
    const std::string text=input;size_t used{};const double value=std::stod(text,&used);
    if(used!=text.size()||!std::isfinite(value))throw std::runtime_error("Invalid number");return value;
}
}
int main(int argc,char** argv){try{
    if(argc!=5&&argc!=7)throw std::runtime_error("Usage: reverb_up_neutral_probe INPUT.wav NEW_OUTPUT.wav [MAIN_RAW SUB1_RAW] SUB2_RAW TAIL_SECONDS");
    const double main=argc==7?number(argv[3]):128,amount=argc==7?number(argv[4]):128;
    const double raw=number(argv[argc==7?5:3]),tail=number(argv[argc==7?6:4]);
    for(const auto control:{main,amount,raw})if(control<0||control>255||std::floor(control)!=control)throw std::runtime_error("Raw controls must be integers 0..255");
    if(tail<0||tail>120)throw std::runtime_error("Tail must be 0..120 seconds");
    if(std::filesystem::exists(argv[2]))throw std::runtime_error("Output must be new");
    const auto input=rmx::readWav(argv[1],180);
    if(input.rate!=48000)throw std::runtime_error("Static Up fixture requires stereo 48 kHz");
    rmx::Sample output;output.rate=48000;output.frames.resize(input.frames.size()+static_cast<size_t>(std::llround(tail*48000)));
    auto selectedDelays=reverbUpDelays;auto gainL=reverbUpGainL,gainR=reverbUpGainR;auto inputA=reverbUpInputA;
    double wetGain=reverbUpWetGain;
    if(argc==7){
        const auto& row=reverbUpControls[static_cast<size_t>(main)];selectedDelays=row.delays;inputA=row.inputA;
        const auto decay=[](double r){return 1+49*std::pow(std::max(0.,r-3)/252,3);};
        const double exponent=decay(128)/decay(amount);
        for(size_t j=0;j<5;++j){gainL[j]=std::pow(row.gainL[j],exponent);gainR[j]=std::pow(row.gainR[j],exponent);}
        wetGain=row.wetGain*reverbUpAmountGain[static_cast<size_t>(amount)]/reverbUpAmountGain[128];
        wetGain*=1+reverbUpMainCorrection[static_cast<size_t>(main)]*reverbUpAmountCorrection[static_cast<size_t>(amount)];
    }
   #ifdef RMX_REVERB_UP_ONE_FRAME_NEGATIVE_CONTROL
    if(argc==7&&main==104)--selectedDelays[4][0];
   #endif
    std::array<std::array<Delay,2>,5> combs;
    for(size_t j=0;j<5;++j)for(size_t ch=0;ch<2;++ch)combs[j][ch]=Delay(static_cast<size_t>(selectedDelays[j][ch]));
    std::array<std::array<Filter,2>,5> feedback;
    for(auto& pair:feedback)for(auto& f:pair){
        f.highpass(25);
        if(argc==7){f.b0=reverbUpFeedback[0];f.b1=reverbUpFeedback[1];f.a1=reverbUpFeedback[2];}
    }
    std::array<Filter,2> inputFilter,high,low;
    const double cutoff=54*std::pow(6310./54,std::max(0.,raw-4)/251);
    for(size_t ch=0;ch<2;++ch){
        auto& f=inputFilter[ch];f.b0=1;f.b1=0;f.b2=-1;f.a1=inputA[0];f.a2=inputA[1];
        high[ch].biquad(cutoff,true);low[ch].biquad(17330,false);
    }
    std::array<std::array<AllPass,2>,2> diffusers{{{AllPass(335),AllPass(1091)},{AllPass(395),AllPass(1031)}}};
    const double gain=wetGain*(1+.5*raw/255);
    for(size_t n=0;n<output.frames.size();++n){
        const auto dry=n<input.frames.size()?input.frames[n]:rmx::Stereo{};
        const std::array<double,2> source{inputFilter[0].tick(dry.l),inputFilter[1].tick(dry.r)};
        std::array<double,2> wet{};
        for(size_t j=0;j<5;++j){
            const double l=combs[j][0].read()*gainL[j],r=combs[j][1].read()*gainR[j];
            wet[0]+=l;wet[1]+=r;
            const double fl=feedback[j][0].tick(l),fr=feedback[j][1].tick(r);
            combs[j][0].push(source[0]+fr);combs[j][1].push(source[1]+fl);
        }
        for(size_t ch=0;ch<2;++ch){for(auto& ap:diffusers[ch])wet[ch]=ap.tick(wet[ch]);wet[ch]=low[ch].tick(high[ch].tick(wet[ch]));}
        output.frames[n]={static_cast<float>(dry.l+gain*wet[0]),static_cast<float>(dry.r+gain*wet[1])};
    }
    rmx::writeWav(argv[2],output);std::cout<<"Rendered independent static Up network\n";
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
