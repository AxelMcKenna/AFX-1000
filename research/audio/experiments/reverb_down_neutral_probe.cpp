// Research-only autonomous candidate; other Main/Sub1 settings remain unmodeled.
#include "rmx/Wav.h"
#include "rmx/Dsp.h"
#include "ReverbDownNeutralCalibration.h"
#include <iostream>

namespace {
struct Delay {
    std::vector<double> data;
    size_t head{};
    void prepare(size_t length) { data.assign(length,0);head=0; }
    double tap() const noexcept { return data[head]; }
    void push(double value) noexcept {data[head]=value;if(++head==data.size())head=0;}
};
struct Filter {
    double b0{},b1{},b2{},a1{},a2{},s1{},s2{};
    void biquad(double hz,bool high) {
        const double w=2*std::numbers::pi*hz/48000,alpha=std::sin(w)/std::sqrt(2.);
        b0=(1+(high?1:-1)*std::cos(w))/2/(1+alpha);b1=(high?-2:2)*b0;b2=b0;
        a1=-2*std::cos(w)/(1+alpha);a2=(1-alpha)/(1+alpha);
    }
    void onePole(double hz,bool high) {
        const double t=std::tan(std::numbers::pi*hz/48000),pole=(1-t)/(1+t);
        b0=high?(1+pole)/2:(1-pole)/2;b1=high?-b0:b0;b2=0;a1=-pole;a2=0;
    }
    double tick(double x) noexcept {
        const double y=b0*x+s1;s1=b1*x-a1*y+s2;s2=b2*x-a2*y;return y;
    }
};
struct AllPass {
    Delay delay;
    double tick(double x) noexcept {const double y=delay.tap()-.7*x;delay.push(x+.7*y);return y;}
};
double number(const char* arg) {
    const std::string text=arg;size_t used{};const double value=std::stod(text,&used);
    if(used!=text.size()||!std::isfinite(value))throw std::runtime_error("Invalid number");
    return value;
}
}
int main(int argc,char** argv) {try {
    if(argc!=5)throw std::runtime_error(
        "Usage: reverb_down_neutral_probe INPUT.wav NEW_OUTPUT.wav SUB2_RAW TAIL_SECONDS\n"
        "Research Down Main128/Sub1-128/48-kHz candidate; full Reverb fidelity remains unproven.");
    if(std::filesystem::exists(argv[2]))throw std::runtime_error("Output already exists");
    const double cutoffRaw=number(argv[3]),tail=number(argv[4]);
    if(cutoffRaw<0||cutoffRaw>255||std::floor(cutoffRaw)!=cutoffRaw||tail<0||tail>120)
        throw std::runtime_error("Sub2 must be an integer 0..255; tail must be 0..120 seconds");
    const auto input=rmx::readWav(argv[1],180);
    if(input.rate!=48000)throw std::runtime_error("Research candidate requires 48 kHz");
    rmx::Sample output;output.rate=48000;
    output.frames.resize(input.frames.size()+static_cast<size_t>(std::llround(tail*48000)));
    std::array<std::array<Delay,2>,5> combs;
    for(size_t j=0;j<5;++j)for(size_t ch=0;ch<2;++ch)combs[j][ch].prepare(reverbDownDelays[j][ch]);
    std::array<std::array<Filter,4>,2> filters;
    const double position=std::max(0.,cutoffRaw-4)/251;
    const double cutoff=17330*std::pow(261./17330,position);
    const double gain=reverbDownWetGain*(1+.5*cutoffRaw/255);
    for(auto& chain:filters) {
        chain[0].onePole(80,true);chain[1].onePole(10000,false);
        chain[2].biquad(54,true);chain[3].biquad(cutoff,false);
    }
    std::array<std::array<AllPass,2>,2> diffusers;
    diffusers[0][0].delay.prepare(335);diffusers[0][1].delay.prepare(1091);
    diffusers[1][0].delay.prepare(395);diffusers[1][1].delay.prepare(1031);
    for(size_t n=0;n<output.frames.size();++n) {
        const auto dry=n<input.frames.size()?input.frames[n]:rmx::Stereo{};
        std::array<double,2> source{dry.l,dry.r},wet{};
        for(size_t ch=0;ch<2;++ch)for(auto& filter:filters[ch])source[ch]=filter.tick(source[ch]);
        for(size_t j=0;j<5;++j) {
            const double left=combs[j][0].tap()*reverbDownGainL[j];
            const double right=combs[j][1].tap()*reverbDownGainR[j];
            combs[j][0].push(source[0]+right);combs[j][1].push(source[1]+left);
            wet[0]+=left;wet[1]+=right;
        }
        for(size_t ch=0;ch<2;++ch)for(auto& diffuser:diffusers[ch])wet[ch]=diffuser.tick(wet[ch]);
        output.frames[n]={static_cast<float>(dry.l+gain*wet[0]),static_cast<float>(dry.r+gain*wet[1])};
    }
    rmx::writeWav(argv[2],output);
    std::cout<<"Rendered autonomous Down Main128/Sub1-128 research candidate\n";
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
