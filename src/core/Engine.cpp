#include "rmx/Engine.h"
#include <numbers>

namespace rmx {
namespace {
constexpr float pi=std::numbers::pi_v<float>;
float db(float x) noexcept { return std::pow(10.f,x/20.f); }
float coefficient(float hz,double sr) noexcept { return 1-std::exp(-2*pi*hz/static_cast<float>(sr)); }
Stereo finite(Stereo x) noexcept { return {std::isfinite(x.l)?std::clamp(x.l,-16.f,16.f):0, std::isfinite(x.r)?std::clamp(x.r,-16.f,16.f):0}; }
float level(Stereo x) noexcept { return std::max(std::abs(x.l),std::abs(x.r)); }
}
Stereo Engine::Delay::read(double ago) const noexcept {
    ago=std::clamp(ago,1.,static_cast<double>(buffer.size()-2));
    double pos=static_cast<double>(head)-ago;
    if(pos<0) pos+=buffer.size();
    const auto index=static_cast<size_t>(pos);
    return mix(buffer[index],buffer[(index+1)%buffer.size()],static_cast<float>(pos-index));
}
void Engine::prepare(double sampleRate,uint32_t maxBlock) {
    (void)maxBlock;
    sr=std::clamp(sampleRate,8000.,192000.);
    const auto capacity=static_cast<size_t>(sr*16)+4;
    sceneDelay.prepare(capacity); history.prepare(capacity); rollHistory.prepare(capacity);
    for(auto& bus:bandLoops) for(auto& band:bus) { band.history.prepare(static_cast<size_t>(sr)+4); band.frozen.assign(static_cast<size_t>(sr)+4,{}); }
    capturedRoll.assign(static_cast<size_t>(sr*8)+4,{});
    constexpr std::array<double,8> seconds{.0297,.0371,.0411,.0437,.0531,.0613,.0719,.0797};
    for(size_t i=0;i<8;++i) reverb[i].prepare(static_cast<size_t>(seconds[i]*sr*2)+3);
    smoothing=1-std::exp(-1.f/static_cast<float>(sr*.008));
    tempoTracker.prepare(sr);
    reset();
}
void Engine::reset() noexcept {
    sceneDelay.clear(); history.clear(); rollHistory.clear();
    for(auto& bus:bandLoops) for(auto& band:bus) { band.history.clear(); band.active=false; band.copied=0; band.position=0; band.length=0; }
    for(auto& delay:reverb) delay.clear();
    lowSplit={}; highSplit={}; sceneFilter={}; feedbackFilter={}; reverbDamping={};
    voices={}; pendingCount=0; sequence={}; sequenceSize=0;
    frame=0; beat=0; bpm=params.get(Param::Tempo); lastTap=0;
    rollPad=-1; selectedPad=0; sourceRoll=false; capturedLength=0; captureCopied=0; capturePosition=0; captureFrame=0;
    rollNext=0; rollStart=0; sceneRead=0; releaseRead=0; releaseAge=0; lastTick=-1;
    previousRelease=false; previousOverdub=false;
    bypassMix=params.get(Param::Bypass); sceneMix=0; releaseMix=0;
    p=params.snapshot(); smooth=p;
    isolateInputMix=(get(Param::IsolateSource)==0||get(Param::IsolateSource)==2)?1.f:0.f;
    isolatePadMix=(get(Param::IsolateSource)==1||get(Param::IsolateSource)==2)?1.f:0.f;
    sceneInputMix=(get(Param::SceneSource)==0||get(Param::SceneSource)==2)?1.f:0.f;
    scenePadMix=(get(Param::SceneSource)==1||get(Param::SceneSource)==2)?1.f:0.f;
    tempoTracker.reset();
    Event e; while(queue.pop(e)) {}
}
bool Engine::enqueue(Event e) noexcept {
    if(queue.push(e)) return true;
    meters.droppedEvents.fetch_add(1,std::memory_order_relaxed); return false;
}
float Engine::noise() noexcept { random^=random<<13; random^=random>>17; random^=random<<5; return static_cast<float>(static_cast<int32_t>(random))/2147483648.f; }
void Engine::trigger(int pad,float velocity) noexcept {
    selectedPad=pad%4;
    if(get(Param::XSource)>.5f) {
        capturedLength=std::min(capturedRoll.size(),static_cast<size_t>(sr*60/bpm*beatDivisions[static_cast<size_t>(get(Param::XRoll))]));
        captureCopied=0; captureFrame=frame; capturePosition=0; sourceRoll=true; return;
    }
    Voice* voice=&voices[0];
    for(auto& v:voices) { if(v.slot<0) { voice=&v; break; } if(v.age>voice->age) voice=&v; }
    *voice={static_cast<int>(get(Param::Bank))*4+pad%4,0,std::clamp(velocity,0.f,1.f),0};
}
void Engine::schedule(int pad,float velocity) noexcept {
    double distance=0;
    if(get(Param::Quantize)>.5f) {
        double target=std::ceil(beat*4-1.e-7)/4;
        if(static_cast<int>(std::round(target*4))%2) target+=get(Param::Swing)*.25;
        distance=std::max(0.,target-beat)*60/bpm*sr;
    }
    if(pendingCount<pending.size()) pending[pendingCount++]={frame+static_cast<uint64_t>(distance),static_cast<uint8_t>(pad%4),velocity,get(Param::Overdub)>.5f};
    else meters.droppedEvents.fetch_add(1,std::memory_order_relaxed);
}
void Engine::event(Event e) noexcept {
    switch(e.type) {
        case EventType::Trigger: schedule(e.pad,e.velocity); break;
        case EventType::RollStart: rollPad=e.pad%4; selectedPad=rollPad; rollNext=beat; rollStart=beat; break;
        case EventType::RollStop: if(get(Param::XHold)<.5f) { rollPad=-1; sourceRoll=false; } break;
        case EventType::ClearSequence: sequence={}; sequenceSize=0; break;
        case EventType::Panic:
            voices={}; rollPad=-1; sourceRoll=false; pendingCount=0; sequence={}; sequenceSize=0;
            params.set(Param::SceneOn,0); params.set(Param::ReleaseAmount,0); params.set(Param::Low,0); params.set(Param::Mid,0); params.set(Param::High,0); params.set(Param::XHold,0); params.set(Param::Overdub,0);
            p=params.snapshot(); break;
        case EventType::Tap:
            if(lastTap>0) { const double tapped=60*sr/(frame-lastTap); if(tapped>=40&&tapped<=240) { params.set(Param::Tempo,static_cast<float>(tapped)); params.set(Param::AutoTempo,0); bpm=tapped; } }
            lastTap=frame?frame:1; beat=std::floor(beat); break;
    }
}
Stereo Engine::sample() noexcept {
    Stereo out{};
    if(!samples) return out;
    const double ratio=std::pow(2.,sm(Param::XPitch)/12.);
    for(auto& v:voices) {
        if(v.slot<0) continue;
        const auto& asset=samples->slots[static_cast<size_t>(v.slot)];
        const auto index=static_cast<size_t>(v.position);
        if(index+1>=asset.frames.size()) { v.slot=-1; continue; }
        const float fade=std::min(1.f,static_cast<float>(v.age)/32.f)*std::min(1.f,static_cast<float>(asset.frames.size()-index)/64.f);
        out=out+mix(asset.frames[index],asset.frames[index+1],static_cast<float>(v.position-index))*(v.velocity*fade);
        v.position+=ratio*asset.rate/sr; ++v.age;
    }
    if(sourceRoll&&capturedLength>1) {
        // Copy the frozen window incrementally: never copy seconds of audio in one callback.
        for(int copied=0;copied<32&&captureCopied<capturedLength;++copied,++captureCopied)
            capturedRoll[captureCopied]=rollHistory.read(static_cast<double>(frame-captureFrame+capturedLength-captureCopied));
        const auto i=static_cast<size_t>(capturePosition)%capturedLength;
        const float fade=std::min(1.f,static_cast<float>(i)/32.f)*std::min(1.f,static_cast<float>(capturedLength-i)/32.f);
        auto captured=[&](size_t index) { return index<captureCopied?capturedRoll[index]:rollHistory.read(static_cast<double>(frame-captureFrame+capturedLength-index)); };
        out=out+mix(captured(i),captured((i+1)%capturedLength),static_cast<float>(capturePosition-std::floor(capturePosition)))*fade;
        capturePosition+=ratio;
        if(capturePosition>=capturedLength) { capturePosition=std::fmod(capturePosition,static_cast<double>(capturedLength)); if(rollPad<0) sourceRoll=false; }
    }
    return out*(sm(Param::XLevel)*(1-sm(Param::SamplerMute)));
}
Stereo Engine::isolate(Stereo x,size_t bus) noexcept {
    Stereo low=lowSplit[bus].low(x,lowAlpha), upper=highSplit[bus].low(x,highAlpha);
    std::array<Stereo,3> bands{low,upper-low,x-upper};
    const int mode=static_cast<int>(get(Param::IsolateMode));
    Stereo out{};
    for(size_t b=0;b<3;++b) {
        const float k=sm(static_cast<Param>(static_cast<int>(Param::Low)+b));
        Stereo y=bands[b];
        auto& loop=bandLoops[bus][b]; loop.history.push(y);
        if(mode!=2||k<=.0001f) loop.active=false;
        if(mode==0) y=y*(k<0?1+k:1+k*2);
        else if(mode==1) {
            const float gate=static_cast<float>(std::fmod(beat*4,1.)<.5);
            y=k<0?y*(1+k):y*(1+k*gate*2);
        } else if(mode==2) {
            const double phase=std::fmod(beat*4,1.);
            const float gate=static_cast<float>(phase<.5);
            if(k<0) y=y*(1+k*(1-gate));
            else if(k>.0001f) {
                const auto length=std::max(size_t(8),static_cast<size_t>(60*sr/bpm*.25/std::pow(2.,std::floor(k*4))));
                if(!loop.active||loop.length!=length) { loop.active=true; loop.length=std::min(length,loop.frozen.size()); loop.copied=0; loop.position=0; loop.start=frame; }
                for(int n=0;n<4&&loop.copied<loop.length;++n,++loop.copied) loop.frozen[loop.copied]=loop.history.read(static_cast<double>(frame-loop.start+loop.length-loop.copied));
                const auto index=static_cast<size_t>(loop.position);
                auto read=[&](size_t i) { return i<loop.copied?loop.frozen[i]:loop.history.read(static_cast<double>(frame-loop.start+loop.length-i)); };
                const float fade=std::min(1.f,static_cast<float>(index)/16)*std::min(1.f,static_cast<float>(loop.length-index)/16);
                y=mix(y,read(index)*fade,k);
                loop.position+=1; if(loop.position>=loop.length) loop.position=0;
            }
        } else {
            const float magnitude=level(y);
            if(k<0) { const float threshold=-k*.2f; y=y*std::clamp((magnitude-threshold)*50.f,0.f,1.f); }
            else if(k>1.e-5f) { const float drive=1+k*12; y={std::tanh(y.l*drive)/std::sqrt(drive),std::tanh(y.r*drive)/std::sqrt(drive)}; }
        }
        out=out+y;
    }
    return out;
}
Stereo Engine::room(Stereo x) noexcept {
    constexpr std::array<double,8> seconds{.0297,.0371,.0411,.0437,.0531,.0613,.0719,.0797};
    std::array<Stereo,8> taps{}; Stereo sum{}, wet{};
    const float size=.35f+get(Param::SceneTime)/7*1.4f;
    const float decay=std::clamp(sm(Param::ReverbDecay)*.7f+sm(Param::SceneResonance)*.28f,.1f,.95f);
    for(size_t i=0;i<8;++i) { taps[i]=reverbDamping[i].low(reverb[i].read(sr*seconds[i]*size),.12f+sm(Param::SceneResonance)*.3f); sum=sum+taps[i]; wet=wet+taps[i]*(i%2?.16f:-.16f); }
    for(size_t i=0;i<8;++i) reverb[i].push(finite(x*.2f+(sum*.25f-taps[i])*decay));
    return {wet.l+sum.r*.1f,wet.r+sum.l*.1f};
}
Stereo Engine::scene(Stereo x) noexcept {
    const int type=static_cast<int>(get(Param::SceneType));
    const float depth=sm(Param::SceneDepth);
    const double delay=std::clamp(sr*60/bpm*beatDivisions[static_cast<size_t>(get(Param::SceneTime))],2.,sr*14);
    Stereo echo=sceneDelay.read(delay), send=x, wet=echo;
    const float cutoff=300+depth*10000;
    if(type==0) { const Stereo lo=sceneFilter.low(x,coefficient(cutoff,sr)); send=lo-feedbackFilter.low(lo,coefficient(cutoff*.35f,sr)); wet=echo; }
    if(type==2) { const float n=noise()*.35f; send=sceneFilter.low({n,n},coefficient(300+sm(Param::NoiseColor)*12000,sr)); wet=send+echo*.5f; }
    if(type==3||type==8) {
        const double speed=std::pow(2.,static_cast<double>(depth)*(type==3?1:-1));
        sceneRead+=1-speed; if(sceneRead<0) sceneRead+=delay; if(sceneRead>=delay) sceneRead-=delay;
        const double phase=sceneRead/delay;
        const float weight=static_cast<float>(.5-.5*std::cos(2*pi*phase));
        wet=sceneDelay.read(2+sceneRead)*weight+sceneDelay.read(2+std::fmod(sceneRead+delay*.5,delay))*(1-weight);
    }
    if(type==5) send=x-sceneFilter.low(x,coefficient(80+depth*7000,sr));
    if(type==6) send=sceneFilter.low(x,coefficient(18000*std::pow(.02f,depth),sr));
    if(type==7) { const float steps=std::pow(2.f,14-depth*11); send={std::round(x.l*steps)/steps,std::round(x.r*steps)/steps}; wet=echo+send*.3f; }
    if(type==4||type==9) wet=room(type==9?x*(1-depth*.8f):x);
    else (void)room({}); // Allow existing reverb to decay without stale frozen state.
    const float feedback=std::min(.96f,sm(Param::Feedback)*(.7f+sm(Param::SceneResonance)*.6f));
    sceneDelay.push(finite(send*sceneMix+echo*feedback));
    const float amount=depth*sceneMix;
    if(type==2) return x+wet*amount;
    if(type>=5) return mix(x,send*(1-depth*.7f)+wet*depth,sceneMix*depth);
    return x+wet*(amount*.8f);
}
Stereo Engine::release(Stereo x) noexcept {
    const bool active=get(Param::ReleaseAmount)>.005f;
    if(active&&!previousRelease) { releaseAge=0; releaseRead=0; }
    if(!active&&previousRelease) {
        params.set(Param::SceneOn,0); params.set(Param::Low,0); params.set(Param::Mid,0); params.set(Param::High,0); params.set(Param::XHold,0); params.set(Param::Overdub,0);
        p=params.snapshot(); rollPad=-1; sourceRoll=false; voices={}; sequenceSize=0; pendingCount=0;
    }
    previousRelease=active;
    releaseMix+=(static_cast<float>(active)-releaseMix)*smoothing;
    Stereo wet{};
    if(active||releaseMix>.0001f) {
        const float lever=sm(Param::ReleaseAmount);
        const double duration=std::max(.05,static_cast<double>(get(Param::ReleaseTime))*60/bpm)*(2.5-1.5*lever)*sr;
        const int type=static_cast<int>(get(Param::ReleaseType));
        if(type==0) { releaseRead+=1+lever*3*std::exp(-releaseAge/duration); wet=history.read(releaseAge+releaseRead+1)*static_cast<float>(std::exp(-releaseAge/(duration*2))); }
        else if(type==1) { const double length=std::min(sr*8.,sr*60/bpm*(lever<.5?1.:lever<.85?.5:.25)); wet=history.read(releaseAge+length-std::fmod(releaseAge,length))*static_cast<float>(std::pow(.35+.3*lever,releaseAge/length)); }
        else { const double speed=std::max(0.,1-releaseAge/duration); releaseRead+=speed; wet=history.read(releaseAge-releaseRead+2)*static_cast<float>(speed); }
        ++releaseAge;
    }
    history.push(x);
    return mix(x,wet,releaseMix);
}
void Engine::detectTempo(Stereo x) noexcept {
    tempoTracker.process(x.l,x.r);
    if(frame%256==0) {
        meters.confidence.store(tempoTracker.certainty(),std::memory_order_relaxed);
        if(get(Param::AutoTempo)>.5f&&tempoTracker.certainty()>.15f) bpm=tempoTracker.bpm();
    }
}
void Engine::process(const float* left,const float* right,float* outL,float* outR,uint32_t frames,Transport transport,std::span<const Event> events) noexcept {
    if(!frames) return;
    p=params.snapshot();
    if(get(Param::UserSettings)<.5f) for(auto setting:{Param::LowCrossover,Param::HighCrossover,Param::Feedback,Param::ReverbDecay,Param::NoiseColor,Param::Swing}) p[static_cast<size_t>(setting)]=parameters[static_cast<size_t>(setting)].initial;
    if(transport.synced&&std::isfinite(transport.bpm)&&transport.bpm>=40&&transport.bpm<=240) { bpm=transport.bpm; if(std::isfinite(transport.beat)) beat=transport.beat; }
    else if(get(Param::AutoTempo)<.5f) bpm=get(Param::Tempo);
    lowAlpha=coefficient(get(Param::LowCrossover),sr); highAlpha=coefficient(get(Param::HighCrossover),sr);
    Event e; while(queue.pop(e)) event(e);
    size_t eventIndex=0;
    float inputPeak=0,outputPeak=0;
    for(uint32_t i=0;i<frames;++i,++frame) {
        while(eventIndex<events.size()&&events[eventIndex].offset<=i) event(events[eventIndex++]);
        for(size_t k=0;k<parameterCount;++k) smooth[k]+=(p[k]-smooth[k])*smoothing;
        const int tick=static_cast<int>(std::floor(beat*24+1.e-7))%384;
        if(tick!=lastTick&&transport.playing) {
            for(size_t j=0;j<sequenceSize;++j) if(sequence[j].active&&sequence[j].tick==tick) trigger(sequence[j].pad,sequence[j].velocity);
            lastTick=tick;
        }
        for(size_t j=0;j<pendingCount;) {
            if(pending[j].at<=frame) {
                const auto pendingEvent=pending[j]; trigger(pendingEvent.pad,pendingEvent.velocity);
                if(pendingEvent.record&&sequenceSize<sequence.size()) {
                    const auto tick=static_cast<uint16_t>(static_cast<int>(std::round(beat*24))%384);
                    sequence[sequenceSize++]={pendingEvent.pad,pendingEvent.velocity,tick,true};
                }
                pending[j]=pending[--pendingCount];
            } else ++j;
        }
        if(rollPad>=0&&beat>=rollNext) { trigger(rollPad,1); rollNext=beat+beatDivisions[static_cast<size_t>(get(Param::XRoll))]; }
        Stereo raw{left?left[i]:0,right?right[i]:(left?left[i]:0)}; raw=finite(raw);
        Stereo input=raw*db(sm(Param::InputGain));
        inputPeak=std::max(inputPeak,level(input));
        if(!transport.synced) detectTempo(input);
        rollHistory.push(input);
        Stereo drums=sample(), processed{};
        const int isoSource=static_cast<int>(get(Param::IsolateSource));
        isolateInputMix+=(((isoSource==0||isoSource==2)?1.f:0.f)-isolateInputMix)*smoothing;
        isolatePadMix+=(((isoSource==1||isoSource==2)?1.f:0.f)-isolatePadMix)*smoothing;
        input=mix(input,isolate(input,0),isolateInputMix); drums=mix(drums,isolate(drums,1),isolatePadMix);
        const int sceneSource=static_cast<int>(get(Param::SceneSource));
        sceneInputMix+=(((sceneSource==0||sceneSource==2)?1.f:0.f)-sceneInputMix)*smoothing;
        scenePadMix+=(((sceneSource==1||sceneSource==2)?1.f:0.f)-scenePadMix)*smoothing;
        sceneMix+=(get(Param::SceneOn)*std::max(sceneInputMix,scenePadMix)-sceneMix)*smoothing;
        const Stereo send=input*sceneInputMix+drums*scenePadMix;
        processed=input+drums+(scene(send)-send);
        processed=release(processed);
        if(get(Param::WetOnly)>.5f) processed=processed-raw*db(sm(Param::InputGain));
        processed=processed*db(sm(Param::OutputGain));
        bypassMix+=(get(Param::Bypass)-bypassMix)*smoothing;
        processed=finite(mix(processed,raw,bypassMix));
        // Transparent below unity; bounded soft protection above unity.
        auto protect=[](float v) { const float a=std::abs(v); return a<=1?v:std::copysign(1+.25f*std::tanh((a-1)*4),v); };
        outL[i]=protect(processed.l); outR[i]=protect(processed.r);
        outputPeak=std::max(outputPeak,level({outL[i],outR[i]}));
        if(transport.playing) beat+=bpm/(60*sr);
    }
    meters.input.store(inputPeak,std::memory_order_relaxed); meters.output.store(outputPeak,std::memory_order_relaxed); meters.tempo.store(static_cast<float>(bpm),std::memory_order_relaxed);
}

SampleBank makeFactoryBank(double rate) {
    SampleBank bank;
    for(int slot=0;slot<16;++slot) {
        auto& s=bank.slots[static_cast<size_t>(slot)]; s.rate=rate;
        const int type=slot%4, variation=slot/4;
        const double length=type==0?.7:type==1?.38:type==2?.32:.16;
        s.frames.resize(static_cast<size_t>(rate*length));
        uint32_t random=0x749abc+static_cast<uint32_t>(slot); double phase=0; float low=0;
        for(size_t i=0;i<s.frames.size();++i) {
            double t=i/rate; random^=random<<13; random^=random>>17; random^=random<<5;
            const float n=static_cast<float>(static_cast<int32_t>(random))/2147483648.f;
            phase+=2*pi*(45+variation*6+100*std::exp(-t*35))/rate;
            low+=.2f*(n-low); float value=0;
            if(type==0) value=static_cast<float>(std::sin(phase)*std::exp(-t*(8+variation))*.85+n*std::exp(-t*220)*.15);
            if(type==1) value=static_cast<float>(n*std::exp(-t*20)*.55+std::sin(2*pi*(170+variation*20)*t)*std::exp(-t*28)*.3);
            if(type==2) { double pulse=std::fmod(t,.011); value=static_cast<float>((n-low)*std::exp(-t*20)*(.35+.3*std::exp(-pulse*300))); }
            if(type==3) value=static_cast<float>((n-low)*std::exp(-t*(45-variation*5))*.5);
            s.frames[i]={value,value};
        }
    }
    return bank;
}
}
