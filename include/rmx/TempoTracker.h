#pragma once
#include <array>
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>

namespace rmx {
// Incremental stereo onset autocorrelation. One lag is evaluated per 5 ms hop;
// the sweep's final hop adds four octave checks (at most 800 pairs each).
// Storage and work are bounded; process never allocates.
// This estimates a pulse, not a bar/downbeat. Host/MIDI/Link grids take priority.
class TempoTracker {
public:
    void prepare(double rate) noexcept {
        sr=std::isfinite(rate)?std::clamp(rate,8000.,192000.):48000.;
        lowAlpha=static_cast<float>(1-std::exp(-2*pi*250/sr));
        hop=std::max(1,static_cast<int>(std::round(sr/200)));
        tickRate=sr/hop;
        minLag=static_cast<int>(std::ceil(60*tickRate/180));
        maxLag=static_cast<int>(std::floor(60*tickRate/70));
        reset();
    }
    void reset() noexcept {
        novelty.fill(0); head=0; age=0; samples=0; energy=0; previous=0;
        mean=0; lag=minLag; best=0; bestLag=100; tempo=120; confidence=0;
        low=0; lowRight=0; phaseAtHop=0; phaseConfidence=0;
        quietHops=0; hopsSinceOnset=0; onsetMean=0; clearedForSilence=false;
    }
    void process(float left,float right) noexcept {
        left=std::isfinite(left)?std::clamp(left,-16.f,16.f):0;
        right=std::isfinite(right)?std::clamp(right,-16.f,16.f):0;
        low+=(left-low)*lowAlpha; lowRight+=(right-lowRight)*lowAlpha;
        // Measure channels independently so anti-phase stereo does not cancel.
        energy+=(low*low+lowRight*lowRight)*.5f+.04f*(left*left+right*right);
        if(++samples<hop) return;
        const float level=std::sqrt(energy/hop); energy=0; samples=0;
        phaseAtHop=wrap(phaseAtHop+tempo/(60*tickRate));
        mean+=(level-mean)*.025f;
        const float onset=std::min(4.f,std::max(0.f,level-previous)/(mean+.003f));
        previous=level; onsetMean+=(onset-onsetMean)*.025f;
        novelty[head]=onset; head=(head+1)%novelty.size();
        age=std::min(age+1,novelty.size());
        if(onset>.08f) hopsSinceOnset=0; else ++hopsSinceOnset;
        if(level<.0003f) ++quietHops; else { quietHops=0; clearedForSilence=false; }
        // Silence cannot retain a valid grid from the preceding track. Keep
        // the last displayed BPM but make its uncertainty explicit immediately.
        if(quietHops>static_cast<unsigned>(tickRate*.35)||hopsSinceOnset>static_cast<unsigned>(tickRate*1.5)) {
            confidence*=.96f; phaseConfidence*=.96f;
        }
        if(quietHops>static_cast<unsigned>(tickRate*.75)) {
            confidence=0; phaseConfidence=0;
            if(!clearedForSilence) {
                novelty.fill(0); age=0; lag=minLag; best=0;
                clearedForSilence=true;
            }
            return;
        }
        if(age<static_cast<size_t>(tickRate*2)) return;
        // A four-second rolling window lets a new track replace old tempo
        // evidence without carrying an eight-second crossfade average.
        const size_t window=std::min(age,static_cast<size_t>(tickRate*4));
        if(window>static_cast<size_t>(lag*2)) {
            const float score=correlationScore(lag,window);
            // Prefer the faster first strong pulse over slower repeated peaks.
            if(score>best*1.12f) { best=score; bestLag=lag; }
        }
        if(++lag>maxLag) {
            // The incremental sweep compares windows from different times.
            // Recheck competing octave peaks against the same current window;
            // a small phase-dependent score advantage must not halve a clear
            // faster pulse. Half-hop interpolation avoids favoring the octave
            // simply because its integer lag lands closer to the true period.
            const double original=bestLag;
            const float octaveScore=correlationScore(original,window);
            float fasterScore=0;double fasterLag=original;
            for(int offset=-1;offset<=1;++offset) {
                const double candidate=original/2+offset*.5;
                if(candidate<minLag)continue;
                const float score=correlationScore(candidate,window);
                if(score>fasterScore) {fasterScore=score;fasterLag=candidate;}
            }
            if(fasterScore>.18f&&fasterScore>=octaveScore/1.2f) {bestLag=fasterLag;best=fasterScore;}
            if(best>.18f&&onsetMean>.004f&&quietHops<static_cast<unsigned>(tickRate*.35)) {
                const float candidate=static_cast<float>(60*tickRate/bestLag);
                // Do not spend several seconds averaging unrelated track tempi.
                const bool changed=std::abs(candidate-tempo)>tempo*.08f;
                tempo=confidence<.1f||changed?candidate:tempo+(candidate-tempo)*.5f;
                confidence=std::clamp(best,0.f,1.f);
                estimatePhase(window);
            } else { confidence*=.7f; phaseConfidence*=.7f; }
            lag=minLag; best=0;
        }
    }
    float bpm() const noexcept { return tempo; }
    float certainty() const noexcept { return confidence; }
    // Fractional quarter-note position at the current input sample, [0,1).
    double phase() const noexcept { return wrap(phaseAtHop+samples*tempo/(60*sr)); }
    float phaseCertainty() const noexcept { return phaseConfidence; }
    bool phaseLocked() const noexcept { return confidence>.18f&&phaseConfidence>.2f; }
    // Use as a rate correction, in beats/second, added to a running beat clock.
    // Slewing instead of assigning beat avoids repeated/skipped sequence hits.
    double phaseSlew(double runningBeat) const noexcept {
        if(!phaseLocked()||!std::isfinite(runningBeat)) return 0;
        return std::clamp(std::remainder(phase()-runningBeat,1.)*.75,-.25,.25);
    }
private:
    static constexpr double pi=3.14159265358979323846;
    static double wrap(double value) noexcept { return value-std::floor(value); }
    float recent(size_t i) const noexcept { return novelty[(head+novelty.size()-1-i)%novelty.size()]; }
    float correlationScore(double period,size_t window) const noexcept {
        if(window<=static_cast<size_t>(period*2))return 0;
        const auto integer=static_cast<size_t>(period),begin=static_cast<size_t>(std::ceil(period));
        const float fraction=static_cast<float>(period-integer);
        double sum=0,a1=0,b1=0,a2=0,b2=0;
        for(size_t i=begin;i<window;++i) {
            const float a=recent(i);float b=recent(i-integer);
            if(fraction>0)b+=(recent(i-integer-1)-b)*fraction;
            sum+=a*b;a1+=a;b1+=b;a2+=a*a;b2+=b*b;
        }
        const double count=static_cast<double>(window-begin);
        // Subtract the mean so steady random novelty is not periodic evidence.
        const double covariance=sum-a1*b1/count;
        const double variance=std::max(0.,a2-a1*a1/count)*std::max(0.,b2-b1*b1/count);
        const double correlation=std::max(0.,covariance/std::sqrt(variance+1.e-12));
        const double candidate=60*tickRate/period;
        const double prior=.85+.15*std::exp(-std::pow(std::log2(candidate/120),2)*2);
        return static_cast<float>(correlation*prior);
    }
    void estimatePhase(size_t window) noexcept {
        // Circular mean of onset times at the winning period. The recurrence
        // needs two trig calls per sweep rather than trig inside the window.
        const double omega=2*pi*tempo/(60*tickRate),c=std::cos(omega),s=std::sin(omega);
        double x=std::cos(omega*.5),y=std::sin(omega*.5),sx=0,sy=0,total=0,weight=1;
        for(size_t i=0;i<window;++i) {
            const double amplitude=recent(i)*weight;
            sx+=amplitude*x; sy+=amplitude*y; total+=amplitude;
            const double next=x*c-y*s; y=y*c+x*s; x=next;
            weight*=.998;
        }
        const float coherence=static_cast<float>(std::sqrt(sx*sx+sy*sy)/(total+1.e-12));
        phaseConfidence=std::clamp(coherence*confidence,0.f,1.f);
        if(coherence>.25f&&total>.1) phaseAtHop=wrap(std::atan2(sy,sx)/(2*pi));
    }
    std::array<float,800> novelty{};
    size_t head{},age{};
    int hop{240},samples{},lag{67},minLag{67},maxLag{171};
    double sr{48000},tickRate{200},phaseAtHop{},bestLag{100};
    unsigned quietHops{},hopsSinceOnset{};
    bool clearedForSilence{};
    float energy{},previous{},mean{},low{},lowRight{},lowAlpha{.032f},best{},tempo{120},confidence{},phaseConfidence{},onsetMean{};
};
}
