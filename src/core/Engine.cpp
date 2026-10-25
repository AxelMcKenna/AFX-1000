#include "rmx/Engine.h"
#include "rmx/FactoryDrums.h"
#include "rmx/SampleReader.h"

namespace rmx {
namespace {
// Only performance controls are interpolated per sample. User selectors and
// other discrete settings are consumed once per block, including on the MCU.
constexpr std::array smoothedParameters{Param::InputGain,Param::OutputGain,Param::Low,Param::Mid,Param::High,
    Param::SceneDepth,Param::SceneTime,Param::SceneResonance,Param::XLevel,Param::XPitch,Param::SamplerMute,Param::ReleaseAmount};
float db(float x) noexcept { return std::pow(10.f,x/20.f); }
Stereo finite(Stereo x) noexcept { return {std::isfinite(x.l)?std::clamp(x.l,-16.f,16.f):0, std::isfinite(x.r)?std::clamp(x.r,-16.f,16.f):0}; }
void approach(float& value,float target,float alpha) noexcept {
    value+=(target-value)*alpha;
    // Float one-pole smoothers can otherwise stall just short of 0/1,
    // leaking a dry source through a fully engaged release or bypass.
    if(std::abs(target-value)<1e-4f) value=target;
}
float level(Stereo x) noexcept { return std::max(std::abs(x.l),std::abs(x.r)); }
}
void Engine::prepare(double sampleRate,uint32_t maxBlock) {
    (void)maxBlock;
    sr=std::clamp(sampleRate,8000.,192000.);
    const auto capacity=static_cast<size_t>(sr*16)+4;
    history.prepare(capacity); sceneProcessor.prepare(sr);
    for(auto& isolator:isolators) isolator.prepare(sr);
    // Eight beats at the slowest supported tempo require twelve seconds.
    capturedRoll.assign(static_cast<size_t>(sr*60/40*xPadBeatValues.back())+4,{});
    smoothing=1-std::exp(-1.f/static_cast<float>(sr*.008));
    protectionRelease=1-std::exp(-1.f/static_cast<float>(sr*.05));
    tempoTracker.prepare(sr);
    reset();
}
void Engine::reset() noexcept {
    sceneProcessor.reset(); history.reset(); rollInput={}; rollInputMix=0;
    for(auto& isolator:isolators) isolator.reset();
    voices={}; sequence.clear();
    frame=0; beat=0; bpm=params.get(Param::Tempo); lastTap=0;
    rollPad=-1; selectedPad=0; sourceRoll=false; capturedLength=0; captureCopied=0; capturePosition=0;
    rollNext=0; rollStart=0; releaseRead=0; releaseAge=0; nudgeDirection=0; nudgeOffset=0; tapIntervals={}; tapCount=0; tapIndex=0; tapped=false;
    previousRelease=false; previousOverdub=false;
    bypassMix=params.get(Param::Bypass); sceneMix=0; releaseMix=0;
    p=params.snapshot(); smooth=p;
    protectionGain=1;meters.protectionGain.store(1,std::memory_order_relaxed);
    isolateInputMix=(get(Param::IsolateSource)==0||get(Param::IsolateSource)==2)?1.f:0.f;
    isolatePadMix=(get(Param::IsolateSource)==1||get(Param::IsolateSource)==2)?1.f:0.f;
    sceneInputMix=(get(Param::SceneSource)==0||get(Param::SceneSource)==2)?1.f:0.f;
    scenePadMix=(get(Param::SceneSource)==1||get(Param::SceneSource)==2)?1.f:0.f;
    tempoTracker.reset(); autoPhaseSlew=0; wasExternalSync=false;
    Event e; while(queue.pop(e)) {}
}
bool Engine::enqueue(Event e) noexcept {
    e=captureEvent(e);
    if(queue.push(e)) return true;
    meters.droppedEvents.fetch_add(1,std::memory_order_relaxed); return false;
}
Event Engine::captureEvent(Event e)const noexcept {
    if(e.type==EventType::Trigger||e.type==EventType::SelectPad) {
        if(e.bank==255)e.bank=static_cast<uint8_t>(params.get(Param::Bank));
        if(e.source==255)e.source=static_cast<uint8_t>(params.get(Param::SampleSource));
    }
    return e;
}
void Engine::set(Param parameter,float value) noexcept {
    params.set(parameter,value); p[static_cast<size_t>(parameter)]=params.get(parameter);
}
bool Engine::trigger(int pad,float velocity,int bank,int source,bool toggleLoop) noexcept {
    selectedPad=pad%4;
    const bool internal=(source<0?static_cast<int>(get(Param::SampleSource)):source)==0;
    const int slot=internal?16+pad%4:(bank<0?static_cast<int>(get(Param::Bank)):bank%4)*4+pad%4;
    Voice* voice=&voices[0];
    for(auto& v:voices) { if(v.slot<0) { voice=&v; break; } if(v.age>voice->age) voice=&v; }
    if(samples&&!internal&&samples->slots[slot].playback.loop&&validSamplePlayback(slot,samples->slots[slot].playback))
        for(auto& v:voices)if(v.slot==slot) {
            if(toggleLoop) {stopSample(pad,bank<0?static_cast<int>(get(Param::Bank)):bank,1);return true;}
            voice=&v;break;
        }
    *voice={slot,0,std::clamp(velocity,0.f,1.f),0,{}};
    if(internal) {
        const auto setting=[&](Param first) {return get(static_cast<Param>(static_cast<unsigned>(first)+pad%4));};
        constexpr float decayRates[]{9,15,12,38};
        constexpr float decayFactors[]{1.7f,1,.62f};
        const auto decay=static_cast<size_t>(setting(Param::KickDecay));
        const bool tight=setting(Param::KickEnvelope)>.5f;
        voice->envelope=db(setting(Param::KickGain));
        voice->envelopeStep=std::exp(-(decayRates[pad%4]*(decayFactors[decay]-1)+(tight?3.f:0.f))/static_cast<float>(sr));
        voice->punch=tight?.35f:0.f;voice->punchStep=std::exp(-1.f/static_cast<float>(sr*.012));
    }
    return false;
}
void Engine::stopSample(int pad,int bank,int source) noexcept {
    const int slot=source==0?16+pad%4:(bank%4)*4+pad%4;
    for(auto& voice:voices)if(voice.slot==slot)voice.slot=-1;
}
void Engine::hit(int pad,float velocity,int bank,int source,bool toggleLoop) noexcept {
    if(bank<0)bank=static_cast<int>(get(Param::Bank));
    if(source<0)source=static_cast<int>(get(Param::SampleSource));
    const bool stopped=trigger(pad,velocity,bank,source,toggleLoop);
    if(get(Param::Overdub)>.5f&&!sequence.record(beat+nudgeOffset,{static_cast<unsigned>(pad%4),static_cast<unsigned>(bank),velocity,source==0,stopped}))
        meters.droppedEvents.fetch_add(1,std::memory_order_relaxed);
}
void Engine::event(Event e) noexcept {
    switch(e.type) {
        // Hardware one-shots are immediate, including when QUANTIZE is on.
        case EventType::Trigger: set(Param::XSource,0); hit(e.pad,e.velocity,e.bank==255?-1:e.bank,e.source==255?-1:e.source); break;
        case EventType::SelectPad: selectedPad=e.pad%4;set(Param::XSource,0);break;
        case EventType::RollStart: {
            rollPad=e.pad%4; selectedPad=rollPad; rollStart=beat+nudgeOffset; if(get(Param::XSource)>.5f) sourceRoll=false;
            const double division=xPadDivision(p);
            rollNext=get(Param::Quantize)>.5f?std::ceil(rollStart/division-1e-7)*division:rollStart;
            break;
        }
        case EventType::RollStop: if(get(Param::XHold)<.5f) rollPad=-1; break;
        case EventType::ClearSequence: sequence.clear(); break;
        case EventType::MutePad: sequence.toggleMute(e.pad); break;
        case EventType::DeletePad:
            sequence.erase(e.pad%4);
            for(auto& voice:voices) if(voice.slot>=0&&voice.slot%4==e.pad%4) voice.slot=-1;
            break;
        case EventType::Nudge: nudgeOffset+=(e.velocity<0?-1:1)/96.; break;
        case EventType::NudgeStart: nudgeDirection=e.velocity<0?-1:1; break;
        case EventType::NudgeStop: nudgeDirection=0; break;
        case EventType::Panic:
            voices={}; rollPad=-1; sourceRoll=false; sequence.clear(); nudgeDirection=0; nudgeOffset=0;
            set(Param::SceneOn,0); set(Param::IsolateOn,0); set(Param::ReleaseAmount,0); set(Param::Low,0); set(Param::Mid,0); set(Param::High,0); set(Param::XHold,0); set(Param::Overdub,0);
            break;
        case EventType::Tap:
            if(tapped&&frame>lastTap) {
                const double interval=(frame-lastTap)/sr;
                if(interval>=.25&&interval<=1.5) {
                    tapIntervals[tapIndex++%tapIntervals.size()]=interval; tapCount=std::min(tapCount+1,tapIntervals.size());
                    double sum=0; for(size_t i=0;i<tapCount;++i) sum+=tapIntervals[i];
                    bpm=60*tapCount/sum; set(Param::Tempo,static_cast<float>(bpm)); set(Param::AutoTempo,0);
                } else { tapCount=0; tapIndex=0; }
            }
            lastTap=frame; tapped=true; beat=std::floor(beat); break;
    }
}
Stereo Engine::sample() noexcept {
    Stereo out{};
    const float pitch=sm(Param::XPitch);
    const double ratio=std::pow(2.,pitch*(pitch<0?get(Param::PitchDownRange):get(Param::PitchUpRange))/(24*12.));
    for(auto& v:voices) {
        if(v.slot<0||!samples) continue;
        const auto& asset=v.slot<16?samples->slots[static_cast<size_t>(v.slot)]:samples->internal[static_cast<size_t>(v.slot-16)];
        if(asset.frames.empty()||!std::isfinite(asset.rate)||asset.rate<8000||asset.rate>192000) {v.slot=-1;continue;}
        const bool loop=v.slot<16&&asset.playback.loop&&validSamplePlayback(static_cast<size_t>(v.slot),asset.playback);
        if(v.position>=asset.frames.size()) {
            if(loop)v.position=std::fmod(v.position,static_cast<double>(asset.frames.size()));
            else {v.slot=-1;continue;}
        }
        const auto index=static_cast<size_t>(v.position);
        const float fadeIn=std::min(1.f,(static_cast<float>(v.age)+1)/std::min(v.slot>=16?size_t{4}:size_t{32},asset.frames.size()));
        const float fadeOut=loop?1.f:std::min(1.f,static_cast<float>(asset.frames.size()-index)/std::min(size_t{64},asset.frames.size()));
        const double pitchStep=ratio*asset.rate/sr;
        const Stereo value=loop?v.stretch.process(asset.frames,v.position,pitchStep,
            asset.rate/sr*bpm/asset.playback.bpm,sr,asset.rate):
            readOneShot(asset.frames,v.position,pitchStep);
        out=out+value*(v.velocity*fadeIn*fadeOut*v.envelope*(1+v.punch));
        v.envelope*=std::max(0.f,1+(v.envelopeStep-1)*static_cast<float>(ratio));
        v.punch*=std::max(0.f,1+(v.punchStep-1)*static_cast<float>(ratio));
        if(!loop)v.position+=pitchStep;
        if(v.age<std::numeric_limits<uint32_t>::max())++v.age;
    }
    Stereo roll{};
    if(sourceRoll&&capturedLength>1) {
        if(captureCopied<capturedLength) {
            // The hardware records FROM the touch, not the preceding audio.
            // Monitor live input during the first pass; then repeat that fixed
            // capture. There is no moving recapture on subsequent repetitions.
            capturedRoll[captureCopied++]=rollInput; roll=rollInput;
        } else {
            const auto i=static_cast<size_t>(capturePosition)%capturedLength;
            const float fade=std::min(1.f,static_cast<float>(i)/32.f)*std::min(1.f,static_cast<float>(capturedLength-i)/32.f);
            roll=mix(capturedRoll[i],capturedRoll[(i+1)%capturedLength],static_cast<float>(capturePosition-std::floor(capturePosition)))*fade;
            capturePosition=std::fmod(capturePosition+ratio,static_cast<double>(capturedLength));
        }
    }
    return out*(sm(Param::XLevel)*(1-sm(Param::SamplerMute)))+roll*rollInputMix;
}
Stereo Engine::isolate(Stereo x,size_t bus) noexcept {
    isolators[bus].tempo(bpm);
    return isolators[bus].process(x,{sm(Param::Low),sm(Param::Mid),sm(Param::High)},beat+nudgeOffset);
}
Stereo Engine::scene(Stereo x) noexcept {
    return sceneProcessor.process(x,sm(Param::SceneDepth),sm(Param::SceneTime),sm(Param::SceneResonance),sceneMix,bpm,beat,peak(rollInput));
}
Stereo Engine::release(Stereo x) noexcept {
    const bool active=get(Param::ReleaseAmount)>.005f;
    if(active&&!previousRelease) { releaseAge=0; releaseRead=0; }
    if(!active&&previousRelease) {
        if(get(Param::ReleaseKeepScene)<.5f) set(Param::SceneOn,0);
        if(get(Param::ReleaseKeepIsolate)<.5f) { set(Param::Low,0); set(Param::Mid,0); set(Param::High,0); }
        if(get(Param::ReleaseKeepSampler)<.5f) {
            set(Param::XHold,0); set(Param::Overdub,0); rollPad=-1; sourceRoll=false; voices={}; sequence.clear();
        }
    }
    previousRelease=active;
    approach(releaseMix,static_cast<float>(active),smoothing);
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
        autoPhaseSlew=get(Param::AutoTempo)>.5f&&get(Param::Quantize)>.5f&&tempoTracker.phaseLocked()?tempoTracker.phaseSlew(beat):0;
    }
}
void Engine::process(const float* left,const float* right,float* outL,float* outR,uint32_t frames,Transport transport,std::span<const Event> events) noexcept {
    if(!frames) return;
    p=params.snapshot();
    transport.synced=transport.synced&&std::isfinite(transport.bpm)&&transport.bpm>=40&&transport.bpm<=240;
    if(wasExternalSync&&!transport.synced) { tempoTracker.reset();autoPhaseSlew=0;meters.confidence.store(0,std::memory_order_relaxed); }
    wasExternalSync=transport.synced;
    if(transport.synced) meters.confidence.store(1,std::memory_order_relaxed);
    if(get(Param::UserSettings)<.5f) for(size_t i=0;i<parameterCount;++i) if(parameters[i].advanced) p[i]=parameters[i].initial;
    if(transport.synced&&std::isfinite(transport.bpm)&&transport.bpm>=40&&transport.bpm<=240) { bpm=transport.bpm; if(std::isfinite(transport.beat)) beat=transport.beat; }
    else if(get(Param::AutoTempo)<.5f) bpm=get(Param::Tempo);
    IsolatorSettings iso;
    iso.mode=static_cast<int>(get(Param::IsolateMode));iso.lowHz=get(Param::LowCrossover);iso.highHz=get(Param::HighCrossover);
    for(unsigned b=0;b<3;++b) {
        auto value=[&](Param first){return static_cast<int>(get(static_cast<Param>(static_cast<unsigned>(first)+b)));};
        iso.minimum[b]=value(Param::IsolateMinLow);iso.maximum[b]=value(Param::IsolateMaxLow);
        iso.addPattern[b]=value(Param::AddPatternLow);iso.transPattern[b]=value(Param::TransPatternLow);iso.rollPattern[b]=value(Param::BandRollPatternLow);
        iso.gateDepth[b]=value(Param::GateDepthLow);iso.driveDepth[b]=value(Param::DriveDepthLow);
    }
    iso.kickStrength=static_cast<int>(get(Param::CutKickStrength));iso.cutHpfResonance=get(Param::CutHpfResonance)>.5f;iso.cutLpfResonance=get(Param::CutLpfResonance)>.5f;
    for(auto& isolator:isolators) isolator.configure(iso);
    SceneSettings sceneSettings;sceneSettings.type=static_cast<int>(get(Param::SceneType));
    auto integer=[&](Param p){return static_cast<int>(get(p));};
    sceneSettings.sub2Mode[0]=integer(Param::BpfModMode);sceneSettings.waveform[0]=integer(Param::BpfWave);sceneSettings.resonance[0]=integer(Param::BpfResonance);
    sceneSettings.sub2Mode[5]=integer(Param::HpfModMode);sceneSettings.waveform[5]=integer(Param::HpfWave);sceneSettings.resonance[5]=integer(Param::HpfResonance);
    sceneSettings.sub2Mode[6]=integer(Param::LpfModMode);sceneSettings.waveform[6]=integer(Param::LpfWave);sceneSettings.resonance[6]=integer(Param::LpfResonance);
    sceneSettings.sub2Mode[2]=integer(Param::NoiseModMode);sceneSettings.waveform[2]=integer(Param::NoiseWave);sceneSettings.resonance[2]=integer(Param::NoiseResonance);
    sceneSettings.feedbackCharacter[0]=integer(Param::BpfFeedbackChar);
    sceneSettings.feedbackCharacter[1]=integer(Param::EchoFeedbackChar);
    sceneSettings.feedbackCharacter[3]=integer(Param::SpiralUpFeedbackChar);
    sceneSettings.feedbackCharacter[5]=integer(Param::HpfFeedbackChar);
    sceneSettings.feedbackCharacter[6]=integer(Param::LpfFeedbackChar);
    sceneSettings.feedbackCharacter[7]=integer(Param::CrushFeedbackChar);
    sceneSettings.feedbackCharacter[8]=integer(Param::SpiralDownFeedbackChar);
    sceneSettings.waveform[7]=integer(Param::CrushWave);sceneSettings.width[0]=integer(Param::BpfWidth);sceneSettings.width[2]=integer(Param::NoiseWidth);sceneSettings.width[7]=integer(Param::CrushWidth);
    sceneSettings.noiseMinimum=integer(Param::NoiseMinimum);sceneSettings.noiseMaximum=integer(Param::NoiseMaximum);
    sceneSettings.echoFilter=integer(Param::EchoFilter);sceneSettings.echoFeedbackMode=integer(Param::EchoFeedbackMode);
    sceneSettings.spiralPitchMode={integer(Param::SpiralUpPitchMode),integer(Param::SpiralDownPitchMode)};sceneSettings.spiralTimeSpan={integer(Param::SpiralUpTimeSpan),integer(Param::SpiralDownTimeSpan)};
    sceneSettings.roomSize={integer(Param::ReverbUpRoomSize),integer(Param::ReverbDownRoomSize)};sceneSettings.reverbTime={integer(Param::ReverbUpTime),integer(Param::ReverbDownTime)};
    sceneSettings.width[1]=integer(Param::EchoWidth);
    sceneSettings.reverbFilter={integer(Param::ReverbUpFilter),integer(Param::ReverbDownFilter)};
    for(const auto group:sceneDelayGroups)for(unsigned region=0;region<4;++region)
        sceneSettings.delayBeats[group.scene][region]=integer(static_cast<Param>(static_cast<unsigned>(group.first)+region));
    sceneSettings.feedback=get(Param::Feedback);sceneSettings.decay=get(Param::ReverbDecay);sceneSettings.noiseColor=get(Param::NoiseColor);sceneProcessor.configure(sceneSettings);

    const bool overdub=get(Param::Overdub)>.5f;
    if(!overdub&&previousOverdub) { sequence.clear(); voices={}; }
    previousOverdub=overdub;
    Event e; while(queue.pop(e)) event(e);
    size_t eventIndex=0;
    float inputPeak=0,outputPeak=0,minimumProtection=1;
    for(uint32_t i=0;i<frames;++i,++frame) {
        while(eventIndex<events.size()&&events[eventIndex].offset<=i) event(events[eventIndex++]);
        for(auto parameter:smoothedParameters) {
            const auto k=static_cast<size_t>(parameter);approach(smooth[k],p[k],smoothing);
        }
        const double performanceBeat=beat+nudgeOffset;
        sequence.advance(performanceBeat,transport.playing,[&](Sequencer::Hit hit) {
            if(hit.stop)stopSample(static_cast<int>(hit.pad),static_cast<int>(hit.bank),hit.internal?0:1);
            else trigger(static_cast<int>(hit.pad),hit.velocity,static_cast<int>(hit.bank),hit.internal?0:1);
        });
        if(rollPad>=0&&performanceBeat+1e-8>=rollNext&&transport.playing) {
            if(get(Param::XSource)>.5f) {
                // Freeze once per gesture. Repetition must not capture a new
                // moving window on every cycle of a held roll.
                if(!sourceRoll) {
                    capturedLength=std::min(capturedRoll.size(),static_cast<size_t>(std::llround(sr*60/bpm*xPadDivision(p))));
                    captureCopied=0; capturePosition=0; sourceRoll=true;
                }
            } else hit(rollPad,1,-1,-1,false);
            const double division=xPadDivision(p);
            rollNext=performanceBeat+division;
        }
        Stereo raw{left?left[i]:0,right?right[i]:(left?left[i]:0)}; raw=finite(raw);
        Stereo input=raw*db(sm(Param::InputGain));
        inputPeak=std::max(inputPeak,level(input));
        if(!transport.synced) detectTempo(input);
        rollInput=input;
        const float rollTarget=sourceRoll&&rollPad>=0&&get(Param::XSource)>.5f?std::min(1.f,sm(Param::XLevel))*(1-sm(Param::SamplerMute)):0.f;
        approach(rollInputMix,rollTarget,smoothing);
        if(rollTarget==0&&rollInputMix<1e-6f) sourceRoll=false;
        Stereo drums=sample(), processed{};
        input=input*(1-rollInputMix);
        const int isoSource=static_cast<int>(get(Param::IsolateSource));
        approach(isolateInputMix,(isoSource==0||isoSource==2)?1.f:0.f,smoothing);
        approach(isolatePadMix,(isoSource==1||isoSource==2)?1.f:0.f,smoothing);
        const float isolateEnabled=get(Param::IsolateOn)>.5f?1.f:0.f;
        input=mix(input,isolate(input,0),isolateInputMix*isolateEnabled); drums=mix(drums,isolate(drums,1),isolatePadMix*isolateEnabled);
        const int sceneSource=static_cast<int>(get(Param::SceneSource));
        approach(sceneInputMix,(sceneSource==0||sceneSource==2)?1.f:0.f,smoothing);
        approach(scenePadMix,(sceneSource==1||sceneSource==2)?1.f:0.f,smoothing);
        approach(sceneMix,get(Param::SceneOn),smoothing);
        const Stereo send=input*sceneInputMix+drums*scenePadMix;
        // FX SOURCE selects the whole processing chain, including RELEASE.
        // Unselected sources bypass it. Noise is generated inside scene() even
        // when neither input is selected.
        processed=input+drums-send+release(scene(send));
        if(get(Param::WetOnly)>.5f) processed=processed-raw*db(sm(Param::InputGain));
        processed=processed*db(sm(Param::OutputGain));
        approach(bypassMix,get(Param::Bypass),smoothing);
        processed=finite(mix(processed,raw,bypassMix));
        // Sample-peak ceiling with linked stereo gain. No lookahead, allocation
        // or per-channel saturation; full-scale excess cannot reach the device.
        const float magnitude=level(processed),target=magnitude>.9995f?.9995f/magnitude:1.f;
        if(target<protectionGain)protectionGain=target;
        else protectionGain+=(target-protectionGain)*protectionRelease;
        minimumProtection=std::min(minimumProtection,protectionGain);
        outL[i]=processed.l*protectionGain;outR[i]=processed.r*protectionGain;
        outputPeak=std::max(outputPeak,level({outL[i],outR[i]}));
        if(transport.playing) {
            beat+=bpm/(60*sr);
            // Follow confident detected pulse phase gradually; never jump the
            // sequencer timeline or override an external host/MIDI/Link clock.
            if(!transport.synced&&get(Param::AutoTempo)>.5f&&get(Param::Quantize)>.5f) beat+=autoPhaseSlew/sr;
            nudgeOffset+=nudgeDirection*.02*bpm/(60*sr);
        }
    }
    meters.sequenceSteps.store(static_cast<unsigned>(sequence.size()),std::memory_order_relaxed); meters.padMuteMask.store(sequence.muteMask(),std::memory_order_relaxed);
    meters.protectionGain.store(minimumProtection,std::memory_order_relaxed);
    meters.input.store(inputPeak,std::memory_order_relaxed); meters.output.store(outputPeak,std::memory_order_relaxed); meters.tempo.store(static_cast<float>(bpm),std::memory_order_relaxed);
}

SampleBank makeFactoryBank(double rate,bool fillSampleBanks) {
    SampleBank bank;
    for(int slot=0;slot<(fillSampleBanks?16:4);++slot) {
        auto& s=fillSampleBanks?bank.slots[static_cast<size_t>(slot)]:bank.internal[static_cast<size_t>(slot)]; s.rate=rate;
        s=makeDrumSample(static_cast<unsigned>(slot%4),static_cast<unsigned>(slot/4),rate);
    }
    if(fillSampleBanks)for(size_t pad=0;pad<4;++pad)bank.internal[pad]=bank.slots[pad];
    return bank;
}
}
