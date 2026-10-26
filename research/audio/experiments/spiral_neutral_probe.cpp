// Research-only candidate. It deliberately remains outside the production DSP.
// Sparse-impulse/DC-tail comparisons fail; see ../spiral-core.md.
#include "rmx/Wav.h"
#include "rmx/Dsp.h"
#include "rmx/FactoryEchoReturn.h"
#include "SpiralNeutralCalibration.h"
#include <array>
#include <iostream>

namespace {
struct LowPass {
    double b0{},b1{},b2{},a1{},a2{},s1{},s2{};
    void prepare(double hz,double q) {
        const double w=2*std::numbers::pi*hz/48000,alpha=std::sin(w)/(2*q);
        b0=(1-std::cos(w))/2/(1+alpha);b1=2*b0;b2=b0;
        a1=-2*std::cos(w)/(1+alpha);a2=(1-alpha)/(1+alpha);
    }
    double tick(double x) noexcept {
        const double y=b0*x+s1;s1=b1*x-a1*y+s2;s2=b2*x-a2*y;return y;
    }
};
struct HighPass {
    double pole{},last{},state{};
    double tick(double x) noexcept {
        const double y=(1+pole)/2*(x-last)+pole*state;last=x;state=y;return y;
    }
};
double number(const char* value) {
    const std::string text=value;size_t used{};const double result=std::stod(text,&used);
    if(used!=text.size()||!std::isfinite(result))throw std::runtime_error("Invalid number");
    return result;
}
}

int main(int argc,char** argv) {try {
    if(argc!=6)throw std::runtime_error(
        "Usage: spiral_neutral_probe INPUT.wav NEW_OUTPUT.wav up|down SUB1_RAW TAIL_SECONDS\n"
        "Experimental Main128/Sub2-zero/48-kHz/120-BPM candidate. Full-effect matching fails.");
    if(std::filesystem::exists(argv[2]))throw std::runtime_error("Output already exists");
    const std::string direction=argv[3];
    if(direction!="up"&&direction!="down")throw std::runtime_error("Direction must be up or down");
    const bool down=direction=="down";
    const double rawTime=number(argv[4]),tail=number(argv[5]);
    if(rawTime<0||rawTime>255||std::floor(rawTime)!=rawTime||tail<0||tail>30)
        throw std::runtime_error("Sub1 must be an integer 0..255; tail must be 0..30 seconds");
    const auto input=rmx::readWav(argv[1],180);
    if(input.rate!=48000)throw std::runtime_error("Research candidate requires 48 kHz");
    rmx::Sample output;output.rate=48000;
    output.frames.resize(input.frames.size()+static_cast<size_t>(tail*48000));
    std::array<LowPass,2> sourceFilter,loopFilter;
    std::array<HighPass,2> hp20,hp50,hp450;
    for(size_t ch=0;ch<2;++ch) {
        sourceFilter[ch].prepare(12000,.707);loopFilter[ch].prepare(12100,.7);
        hp20[ch].pole=spiralHighPassPoles[0];hp50[ch].pole=spiralHighPassPoles[1];
        hp450[ch].pole=spiralHighPassPoles[2];
    }
    rmx::FractionalDelay feedback;feedback.prepare(25000);
    rmx::FactoryEchoReturn echoes;echoes.prepare(48000);
    echoes.restart(rmx::FactoryEchoReturn::Profile::spiral);
    const double delay=down?spiralLoopDelay[1]:spiralLoopDelay[0];
    const double feedbackGain=down?1.2:1.5;
    const double gain=down?1:spiralUpOutputScale;
    const size_t latency=down?640:1792;
    std::vector<std::array<double,2>> latencyLine(latency);
    std::array<std::array<double,32>,2> shapeState{};
    size_t shapeHead=0,latencyHead=0;
    double smoothedPeak=0,envelope=0;
    for(size_t block=0;block<output.frames.size();block+=32) {
        double peak=0;
        for(size_t n=block;n<std::min(block+32,input.frames.size());++n)
            peak=std::max(peak,std::abs(static_cast<double>(input.frames[n].l)+input.frames[n].r));
        // Smoothing precedes the maximum hold. Variable-peak noise distinguishes
        // this from smoothing only increases. Release behavior is unresolved.
        smoothedPeak+=spiralEnvelopeAlpha*(peak-smoothedPeak);
        envelope=std::max(envelope,smoothedPeak);
        for(size_t n=block;n<std::min(block+32,output.frames.size());++n) {
            const auto x=n<input.frames.size()?input.frames[n]:rmx::Stereo{};
            // Empirical neutral-clock model. The quiet 34-second capture rules
            // out both an unbounded ramp and a simple sawtooth phase wrap.
            const double phase=2.086162567138672e-6*(static_cast<double>(block)-64);
            const double triangle=1-std::abs(std::fmod(phase+1,4)-2);
            const auto tap=feedback.read(std::floor(delay)+triangle-std::floor(triangle));
            std::array<double,2> z{},wet{};
            for(size_t ch=0;ch<2;++ch) {
                const double inputValue=sourceFilter[ch].tick(ch?x.r:x.l)+(ch?tap.r:tap.l)*feedbackGain;
                const double limited=std::clamp(inputValue,-envelope*.5,envelope*.5);
                z[ch]=loopFilter[ch].tick(hp450[ch].tick(hp50[ch].tick(limited)));
                shapeState[ch][shapeHead]=hp20[ch].tick(z[ch]);
                for(size_t i=0;i<spiralShape.size();++i)
                    wet[ch]+=shapeState[ch][(shapeHead+32-i)%32]*spiralShape[i];
                wet[ch]*=gain;
            }
            feedback.push({static_cast<float>(z[0]),static_cast<float>(z[1])});
            shapeHead=(shapeHead+1)%32;
            const auto delayed=latencyLine[latencyHead];latencyLine[latencyHead]=wet;
            latencyHead=(latencyHead+1)%latency;
            const auto returned=echoes.process(delayed,static_cast<int>(rawTime),1,120);
            output.frames[n]={static_cast<float>(x.l+delayed[0]+returned[0]),
                              static_cast<float>(x.r+delayed[1]+returned[1])};
        }
    }
    rmx::writeWav(argv[2],output);
    std::cout<<"Rendered experimental Spiral hypothesis; full-effect fidelity remains unverified\n";
} catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}}
