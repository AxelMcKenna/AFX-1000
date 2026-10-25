#include "rmx/Scene.h"
#include "rmx/Parameters.h"
#include <numbers>

namespace rmx {
namespace {
constexpr double pi=std::numbers::pi;
constexpr std::array<double,8> roomSeconds{.0297,.0371,.0411,.0437,.0531,.0613,.0719,.0797};
float db(float dB) {return std::pow(10.f,dB/20);}
Stereo bounded(Stereo x) {return {std::clamp(x.l,-8.f,8.f),std::clamp(x.r,-8.f,8.f)};}
float sweep(float position,float bottom=25,float top=18000) {return bottom*std::pow(top/bottom,std::clamp(position,0.f,1.f));}
float noiseLevel(float sub1,int minimum,int maximum) {
    constexpr float minima[]{-1000,-18,-12,-6},maxima[]{0,3,6,9};
    const int raw=std::clamp(static_cast<int>(std::floor(sub1*(255.f/7)+1.e-4f)),0,255);
    const float low=minimum==0?0:db(minima[std::clamp(minimum,0,3)]);
    const float high=db(maxima[std::clamp(maximum,0,3)]),middle=(low+high)*.5f;
    const float gain=raw<124?low+(middle-low)*std::clamp((raw-3)/121.f,0.f,1.f):
        middle+(high-middle)*std::clamp((raw-131)/121.f,0.f,1.f);
    // Calibration audio used the factory -18/+6 dB centre position.
    return gain/((db(-18)+db(6))*.5f);
}
}
void SceneProcessor::prepare(double sampleRate) {
    rate=sampleRate;echo.prepare(static_cast<size_t>(rate*16)+4);spiral.prepare(static_cast<size_t>(rate*.75)+4);
    for(size_t i=0;i<room.size();++i)room[i].prepare(static_cast<size_t>(rate*roomSeconds[i]*2)+4);
    dampingAlpha=poleCoefficient(6000,rate);noiseTilt.configure(1000,.7071f,rate);
    noisePolish.configure(12500,.7071f,rate);
    noiseCutoffSlew=1-std::exp(-1.f/static_cast<float>(rate*.008));
    noiseModSlew=1-std::exp(-1.f/static_cast<float>(rate*.002));noiseReturnAlpha=poleCoefficient(6500,rate);
    sideAttack=1-std::exp(-1.f/static_cast<float>(rate*.003));sideRelease=1-std::exp(-1.f/static_cast<float>(rate*.08));updateRoom();reset();
}
void SceneProcessor::reset() noexcept {
    echo.reset();spiral.reset();for(auto& delay:room)delay.reset();damping={};
    mainFilter.reset();echoFilter.reset();noiseTilt.reset();noisePolish.reset();calibratedNoise.reset();pitchPhase=0;frame=0;random=0x12345678;
    noiseCutoff=90;noiseModGain=1;noiseReturn={};noiseAge=0;
    previousCutoff=previousQ=previousEchoCutoff=-1;sidechainEnvelope=0;roomSide=0;
}
void SceneProcessor::configure(const SceneSettings& next) noexcept {
    if(next==settings)return;
    if(next.type==2&&settings.type!=2) {noiseAge=0;noiseReturn={};}
    settings=next;settings.type=std::clamp(settings.type,0,9);previousCutoff=previousQ=previousEchoCutoff=-1;updateRoom();
}
float SceneProcessor::noise() noexcept {random^=random<<13;random^=random>>17;random^=random<<5;return static_cast<float>(static_cast<int32_t>(random))/2147483648.f;}
float SceneProcessor::modulation(float amount,double beat) const noexcept {
    const double position=std::clamp(beat,-1.e12,1.e12)*(.25+amount*3.75),phase=position-std::floor(position);
    float value=1;
    switch(settings.waveform[settings.type]) {
        case 0:value=static_cast<float>(1-std::abs(phase*2-1));break;
        case 1:value=static_cast<float>(phase);break;
        case 2:value=phase<.5?1.f:0.f;break;
        case 3: {
            double cycle=std::fmod(std::floor(position),4294967296.);if(cycle<0)cycle+=4294967296.;
            uint32_t hash=static_cast<uint32_t>(cycle)^0x9e3779b9;
            hash^=hash>>16;hash*=0x7feb352d;hash^=hash>>15;value=(hash&65535u)/65535.f;break;
        }
        default:value=1-std::clamp(sidechainEnvelope*4,0.f,1.f);break;
    }
    return 1-amount*(1-value);
}
float SceneProcessor::noiseModulation(float amount,double beat) const noexcept {
    if(amount<=0)return 1;
    // Musical divisions, smoothed at the output so square/random edges and
    // changes of subdivision cannot introduce a one-sample gain discontinuity.
    constexpr double rates[]{.25,.5,1,2,4};
    const auto region=std::min(4u,static_cast<unsigned>(amount*5));
    const double position=std::clamp(beat,-1.e12,1.e12)*rates[region];
    const double phase=position-std::floor(position);float wave=1;
    switch(settings.waveform[2]) {
        case 0:wave=static_cast<float>(.5-.5*std::cos(2*pi*phase));break;
        case 1:wave=static_cast<float>(phase);break;
        case 2:wave=phase<.5?1.f:0.f;break;
        case 3: {
            double cycle=std::fmod(std::floor(position),4294967296.);if(cycle<0)cycle+=4294967296.;
            uint32_t hash=static_cast<uint32_t>(cycle)^0x9e3779b9u;hash^=hash>>16;hash*=0x7feb352du;hash^=hash>>15;
            wave=(hash&65535u)/65535.f;break;
        }
        default:wave=1-std::clamp(sidechainEnvelope*4,0.f,1.f);break;
    }
    return 1-amount*(1-wave);
}
void SceneProcessor::updateRoom() noexcept {
    constexpr float timeFactors[]{.5f,1,2};
    for(unsigned side=0;side<2;++side) {
        const float size=settings.roomSize[side]==0?1.65f:.8f;
        const double t60=(.35+settings.decay*4.5)*timeFactors[std::clamp(settings.reverbTime[side],0,2)];
        for(size_t i=0;i<room.size();++i) {
            roomLengths[side][i]=roomSeconds[i]*size*rate;
            roomGains[side][i]=static_cast<float>(std::pow(.001,roomSeconds[i]*size/t60));
        }
    }
}
Stereo SceneProcessor::reverb(Stereo input) noexcept {
    std::array<Stereo,8> taps{};Stereo sum{},output{};
    for(size_t i=0;i<room.size();++i) {
        auto tap=room[i].read(roomLengths[roomSide][i]);
        damping[i]=damping[i]+(tap-damping[i])*dampingAlpha;taps[i]=damping[i];sum=sum+taps[i];output=output+taps[i]*(i%2?.19f:-.19f);
    }
    // Householder feedback matrix; per-line gain is derived from T60 and
    // remains below unity. Filter damping does not change Sub2's output role.
    for(size_t i=0;i<room.size();++i) {
        const float gain=roomGains[roomSide][i];
        room[i].push(bounded(input*.22f+(sum*.25f-taps[i])*gain));
    }
    return {output.l+sum.r*.1f,output.r+sum.l*.1f};
}
Stereo SceneProcessor::process(Stereo input,float macro,float sub1,float sub2,float enabled,double bpm,double beat,float sidechain) noexcept {
    const int type=std::clamp(settings.type,0,9);
    macro=std::clamp(macro,0.f,1.f);sub1=std::clamp(sub1,0.f,7.f);sub2=std::clamp(sub2,0.f,1.f);enabled=std::clamp(enabled,0.f,1.f);
    const bool modulated=type==0||type==2||type==5||type==6||type==7;
    const bool resonance=modulated&&settings.sub2Mode[type]==1;
    const float activation=std::min(1.f,macro*10);
    const auto region=type==1?echoDelayRegion(sub1):sceneDelayRegion(sub1);
    const bool measuredNoise=type==2&&rate==48000&&settings.width[2]==1&&!resonance;
    const auto choice=type==2?(measuredNoise?3:5):std::clamp(settings.delayBeats[type][region],0,type==1?8:6);
    // Original synchronized Echo first truncates the beat period to whole
    // milliseconds, then applies the chosen division. At 128 BPM, a half beat
    // is 11232 frames at 48 kHz, rather than the ideal-clock 11250 frames.
    const double safeBpm=std::clamp(bpm,40.,240.);
    const double beatFrames=(type==1||measuredNoise)?rate*std::floor(60000/safeBpm)/1000:rate*60/safeBpm;
    const double delay=std::clamp(beatFrames*sceneDelayBeats[static_cast<size_t>(choice)],2.,rate*14);
    const auto delayed=echo.read(delay);
    sidechainEnvelope+=(sidechain-sidechainEnvelope)*(sidechain>sidechainEnvelope?sideAttack:sideRelease);
    float cutoff=sweep(macro);
    if(type==2) {noiseCutoff+=(sweep(macro,90,12500)-noiseCutoff)*noiseCutoffSlew;cutoff=noiseCutoff;}
    if(type==6)cutoff=sweep(1-macro);
    if(type==1)cutoff=sweep(settings.echoFilter==2?sub2:1-sub2);
    if(type==1&&settings.echoFilter==2) {
        const int raw=std::clamp(static_cast<int>(std::floor(sub2*255+1.e-4f)),0,255);
        cutoff=60*std::exp(std::max(0,raw-4)*.0168583737f);
    }
    if(type==4)cutoff=sweep(sub2,25,10000);
    if(type==9)cutoff=sweep(1-sub2);
    constexpr float widthQ[]{2,.8f,.5f};
    float q=widthQ[std::clamp(settings.width[type],0,2)];
    if(type==1) {
        constexpr float echoQ[]{2.f,.70710678f,.5f};
        q=echoQ[std::clamp(settings.width[1],0,2)];
    }
    if(type==2) {constexpr float noiseQ[]{2.8f,1.6f,.9f};q=noiseQ[std::clamp(settings.width[2],0,2)];}
    if(resonance) {const int character=settings.resonance[type];if(character!=2)q+=sub2*(character==1?1.3f:7.3f);}
    if((frame&31u)==0||previousCutoff<0) {
        if(cutoff!=previousCutoff||q!=previousQ) {mainFilter.configure(cutoff,q,rate);previousCutoff=cutoff;previousQ=q;}
        // ECHO Sub2 is a filter cutoff, not a feedback/resonance surrogate.
        if(type==1&&(cutoff!=previousEchoCutoff||q!=previousQ)) {echoFilter.configure(cutoff,q,rate);previousEchoCutoff=cutoff;}
    }
    if((type==2||type==7)&&((frame&(type==2?7u:31u))==0||previousEchoCutoff<0)) {
        const float auxCutoff=type==2?cutoff:std::min(12000.f,static_cast<float>(rate*.4));
        echoFilter.configure(auxCutoff,q,rate);previousEchoCutoff=auxCutoff;
    }
    Stereo result=input,send=input;
    constexpr float characters[]{.65f,1.f,1.45f};
    const float feedback=std::min(.96f,settings.feedback*characters[std::clamp(settings.feedbackCharacter[type],0,2)]);
    const float modGain=modulated&&!resonance&&type!=2?modulation(sub2,beat):1;
    if(type==4||type==9) {
        roomSide=type==9?1:0;
        const auto wetRoom=reverb(input*(enabled*activation));
        const auto filtered=mainFilter.process(wetRoom);
        const int filter=settings.reverbFilter[roomSide];
        const auto wet=(filter==2?filtered.high:filter==1?filtered.band*(1/q):filtered.low)*(sub1/7);
        result=type==4?input+wet*(macro*enabled):mix(input,wet,macro*enabled);
        echo.push(delayed*feedback);spiral.push({});
    } else if(type==3||type==8) {
        const unsigned direction=type==8?1:0;
        float semitones=sub2*12;
        if(settings.spiralPitchMode[direction]==1)semitones=std::round(semitones);
        const double speed=std::pow(2.,semitones*(direction?-1:1)/12.);
        constexpr float spans[]{.5f,1,1.5f};
        const double window=rate*(.01+.2*macro)*spans[std::clamp(settings.spiralTimeSpan[direction],0,2)];
        pitchPhase+=(1-speed)/window;pitchPhase-=std::floor(pitchPhase);
        const float weight=static_cast<float>(.5-.5*std::cos(2*pi*pitchPhase));
        const auto shifted=spiral.read(2+window*pitchPhase)*weight+spiral.read(2+window*std::fmod(pitchPhase+.5,1.))*(1-weight);
        spiral.push(bounded(input*enabled*activation+delayed*feedback));echo.push(bounded(shifted));
        result=type==3?input+shifted*(macro*enabled*.8f):mix(input,shifted,macro*enabled);
        (void)reverb({});
    } else {
        const auto filtered=mainFilter.process(input);
        if(type==0)send=filtered.band*(1/q);
        if(type==5)send=filtered.high;
        if(type==6)send=filtered.low;
        if(type==7) {
            const float steps=std::pow(2.f,14-macro*11);
            const Stereo crushed{std::round(input.l*steps)/steps,std::round(input.r*steps)/steps};
            // Bit reduction is followed by a filter before the echo circuit.
            send=echoFilter.process(crushed).low;
        }
        if(measuredNoise) {
            calibratedNoise.configure(static_cast<int>(std::floor(macro*255+1.e-4f)));
            send=calibratedNoise.process({noise(),noise()});
            const auto tilt=noiseTilt.process(send);
            send=mix(send,settings.noiseColor<.5f?tilt.low:tilt.high,std::abs(settings.noiseColor-.5f)*2);
            noiseModGain+=((noiseModulation(sub2,beat))-noiseModGain)*noiseModSlew;
            send=send*(noiseLevel(sub1,settings.noiseMinimum,settings.noiseMaximum)*noiseModGain*enabled);
            const auto returned=noiseAge>=static_cast<uint64_t>(delay)?delayed:Stereo{};
            // Independent tail captures identify a half-beat return of 0.35,
            // recirculating at exactly 0.5. The return survives button-off.
            result=input+send+returned*.35f;
            echo.push(bounded(send+returned*.5f));
            spiral.push({});(void)reverb({});++noiseAge;++frame;
            return result;
        } else if(type==2) {
            const float n=noise()*.28f;const auto generated=echoFilter.process({n,n});
            // Partial energy compensation keeps a sweep from becoming a sudden
            // blast of treble. Resonance still changes the contour audibly.
            const float compensation=std::clamp(std::sqrt(1200.f/cutoff),.45f,2.f);
            send=noisePolish.process(generated.band).low*(compensation/std::sqrt(q));
            const auto tilt=noiseTilt.process(send);
            send=mix(send,settings.noiseColor<.5f?tilt.low:tilt.high,std::abs(settings.noiseColor-.5f)*2);
            constexpr float minima[]{-1000,-18,-12,-6},maxima[]{0,3,6,9};
            const float position=sub1/7,minimum=minima[std::clamp(settings.noiseMinimum,0,3)],maximum=maxima[std::clamp(settings.noiseMaximum,0,3)];
            const float volume=settings.noiseMinimum==0?position*position*db(maximum):db(minimum+(maximum-minimum)*position);
            noiseModGain+=((resonance?1.f:noiseModulation(sub2,beat))-noiseModGain)*noiseModSlew;
            send=send*(volume*noiseModGain*activation);
            // Ignore a previous effect's shared delay contents until this
            // effect has written one delay length. No delay-buffer clear in IO.
            const Stereo returned=noiseAge>=static_cast<uint64_t>(delay)?delayed:Stereo{};
            noiseReturn=noiseReturn+(returned-noiseReturn)*noiseReturnAlpha;
            result=input+(send+noiseReturn*.4f)*enabled;
            ++noiseAge;
        } else if(type==1) {
            const auto wetFiltered=echoFilter.process(delayed);
            const auto wet=settings.echoFilter==2?wetFiltered.high:settings.echoFilter==1?wetFiltered.band*(1/q):wetFiltered.low;
            const auto raw=std::clamp(static_cast<int>(std::floor(macro*255+1.e-4f)),0,255);
            const float amount=std::clamp((raw-3)/189.f,0.f,1.f);
            result=input+wet*(amount*enabled);
        } else if(type==0)result=input+delayed*(macro*enabled*.8f*modGain);
        else result=mix(input,send*modGain+delayed*(macro*modGain),macro*enabled);
        // HOLD freezes the currently circulating echo at the full macro end.
        const bool hold=type==1&&settings.echoFeedbackMode==0&&macro>.985f;
        echo.push(type==2?bounded(send*enabled+noiseReturn*feedback):hold?delayed:bounded(send*(enabled*(type==1?1:activation))+delayed*feedback));
        spiral.push({});(void)reverb({});
    }
    ++frame;return result;
}
}
