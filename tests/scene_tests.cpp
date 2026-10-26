#include "rmx/Scene.h"
#include "rmx/Engine.h"
#include "rmx/State.h"
#include <iostream>
#include <limits>
#include <numbers>
#include <stdexcept>

using namespace rmx;
constexpr double pi=std::numbers::pi;
void require(bool ok,const char* message) {if(!ok)throw std::runtime_error(message);}
float sine(double frequency,size_t i) {return .2f*static_cast<float>(std::sin(2*pi*frequency*i/48000));}
double energy(Stereo x) {return x.l*x.l+x.r*x.r;}
int main() {try {
    {
        // Return component only; the input here stands in for a separately
        // generated pitch stream. This does not exercise a Spiral generator.
        FactoryEchoReturn processor;processor.prepare(48000);
        for(const auto [bpm,delay]:std::array<std::pair<double,size_t>,3>{{{120,12000},{128,11232},{137,10488}}}) {
            processor.reset();processor.restart(FactoryEchoReturn::Profile::spiral);
            const double first=.25*0.7079457843841379*.7*(1-.5/62.25);
            for(size_t i=0;i<=delay*2;++i) {
                const auto output=processor.process(i==0?std::array<double,2>{.25,-.125}:std::array<double,2>{},128,i<100?1:0,bpm);
                if(i<delay)require(output[0]==0&&output[1]==0,"Spiral return arrived before its measured division");
                if(i==delay)require(std::abs(output[0]-first)<1e-7,"Spiral return changed its measured -3 dB send/0.7 return gain");
                if(i==delay*3/2)require(std::abs(output[0]-.25*0.7079457843841379*.7*(.5/62.25))<1e-7,"Spiral return lost its adjacent crossfaded tap");
                if(i==delay*2)require(std::abs(output[0]-first*.75)<1e-7,"Spiral return changed its measured 0.75 feedback");
                require(std::abs(output[0]+output[1]*2)<1e-7,"Spiral return introduced channel coupling");
            }
        }
    }
    {
        for(int raw:{113,177,213,253}) {
            Engine before,after;
            const auto controls=[&](Engine& engine) {
                engine.params.set(Param::AutoTempo,0);engine.params.set(Param::Tempo,120);
                engine.params.set(Param::SceneType,7);engine.params.set(Param::SceneOn,1);
                engine.params.set(Param::SceneDepth,raw/255.f);engine.params.set(Param::SceneTime,128*7.f/255);
                engine.params.set(Param::SceneResonance,0);engine.params.set(Param::IsolateOn,0);
            };
            controls(before);before.prepare(48000,128);after.prepare(48000,128);controls(after);
            std::array<float,128> input{},al{},ar{},bl{},br{};
            for(unsigned block=0;block<1200;++block) {
                for(size_t i=0;i<input.size();++i)input[i]=block<375?0:sine(1037,block*128+i);
                before.process(input.data(),input.data(),al.data(),ar.data(),128);
                after.process(input.data(),input.data(),bl.data(),br.data(),128);
                for(size_t i=0;i<input.size();++i)require(al[i]==bl[i]&&ar[i]==br[i],"Initial host controls changed the settled Crush clock phase");
            }
        }
    }
    {
        // Late original-reference impulses distinguish reciprocal float
        // normalization and float-product rounding from several plausible
        // period formulas that disagree only at recurring sample boundaries.
        struct Capture {int raw;size_t frame;float first,second;};
        constexpr std::array<Capture,4> captures{{
            {113,157445,.0483129732f,.0456286222f},
            {177,140949,.0451216027f,.0394738093f},
            {213,199821,.0414140038f,.0312262550f},
            {253,291869,.0344913155f,.0162173100f}}};
        CalibratedFilterEcho processor;processor.prepare(48000);
        for(const auto& capture:captures) {
            processor.invalidate();
            for(size_t i=0;i<=capture.frame+1;++i) {
                const auto output=processor.process(i==capture.frame?Stereo{.05f,-.04f}:Stereo{},7,capture.raw,0,1,120);
                if(i==capture.frame)require(std::abs(output.l-capture.first)<2e-6f,"Crush hold clock sampled the wrong boundary frame");
                if(i==capture.frame+1)require(std::abs(output.l-capture.second)<2e-6f,"Crush held-input filter differs from reference");
                require(std::abs(output.r+output.l*.8f)<1e-6f,"Crush changed stereo routing");
            }
        }
        for(int raw=0;raw<256;++raw) {
            processor.invalidate();
            for(unsigned i=0;i<1024;++i) {
                const auto output=processor.process(i==64?Stereo{.05f,0}:Stereo{},7,raw,128,1,120);
                require(std::isfinite(output.l)&&std::abs(output.l)<1&&output.r==0,"Crush became unstable across raw control range");
            }
        }
    }
    {
        // Independent original impulse captures, with only the measured
        // 32-frame bypass latency removed. Button-off precedes the first tap.
        constexpr std::array<int,3> types{0,5,6};
        constexpr std::array<std::array<float,4>,3> direct{{
            {1.08466162f,.15784727f,.13931002f,.12431574f},
            {.93282206f,-.07649630f,-.03058010f,-.04923788f},
            {.00900096f,.03353484f,.06030561f,.07965446f}}};
        constexpr std::array<float,3> first{.70622398f,.61455636f,.00592996f};
        for(size_t effect=0;effect<types.size();++effect) {
            SceneProcessor processor;processor.prepare(48000);SceneSettings settings;settings.type=types[effect];processor.configure(settings);
            for(size_t i=0;i<=24000;++i) {
                const auto output=processor.process(i==0?Stereo{.05f,-.04f}:Stereo{},128.f/255,128*7.f/255,0,i<4800?1:0,120,i/24000.,0);
                if(i<4)require(std::abs(output.l-.05f*direct[effect][i])<1e-6f,"Factory filter direct impulse differs from reference");
                if(i==12000)require(std::abs(output.l-.05f*first[effect])<1e-6f,"Factory filter echo disappeared on button-off or changed level");
                if(i==18000)require(std::abs(output.l-.05f*first[effect]*(.5f/61.75f))<1e-6f,"Factory filter Sub1 lost its adjacent crossfaded tap");
                if(i==24000)require(std::abs(output.l-.05f*first[effect]*.75f)<1e-6f,"Factory filter repeat differs from measured 0.75 feedback");
                require(std::abs(output.r+output.l*.8f)<1e-6f,"Factory filter changed stereo routing");
            }
        }
        CalibratedFilterEcho filter;filter.prepare(48000);
        for(int type:types)for(int raw=0;raw<256;++raw) {
            filter.invalidate();
            for(unsigned i=0;i<1024;++i) {
                const auto output=filter.process(i==0?Stereo{.05f,0}:Stereo{},type,raw,128,1,120);
                require(std::isfinite(output.l)&&std::abs(output.l)<1&&output.r==0,"Calibrated filter became unstable across raw control range");
            }
        }
    }
    {
        for(unsigned raw:{0u,65u,66u,131u,132u,193u,194u,255u}) {
            const size_t expected=raw<66?0:raw<132?1:raw<194?2:3;
            require(echoDelayRegion(raw*7.f/255)==expected,"Echo region differs from measured public control boundary");
        }
        for(const auto [bpm,expected]:std::array<std::pair<double,size_t>,5>{{{90,15984},{128,11232},{137,10488},{128.5,11184},{123.9,11616}}}) {
            SceneProcessor processor;processor.prepare(48000);SceneSettings settings;settings.type=1;processor.configure(settings);
            size_t onset=0;
            for(size_t i=0;i<=expected;++i) {
                const auto out=processor.process(i==0?Stereo{.25f,0}:Stereo{},1,128*7.f/255,0,1,bpm,0,0);
                if(i>0&&onset==0&&std::abs(out.l)>1e-5f)onset=i;
            }
            require(onset==expected,"Echo timing differs from measured whole-millisecond beat period");
        }
        SceneProcessor processor;processor.prepare(48000);SceneSettings settings;settings.type=1;processor.configure(settings);
        for(size_t i=0;i<=24000;++i) {
            const auto out=processor.process(i==0?Stereo{.25f,0}:Stereo{},1,128*7.f/255,0,1,120,i/24000.,0);
            if(i==0)require(out.l==.25f,"Factory Echo reduced its dry signal");
            if(i==12000)require(std::abs(out.l-.24861544f)<1e-5f,"Factory Echo first tap differs from measured reference");
            if(i==24000)require(std::abs(out.l-.1740308f)<1e-5f,"Factory Echo repeat differs from measured reference");
            require(out.r==0,"Factory Echo introduced cross-channel output");
        }
    }
    {
        FractionalDelay delay;
        require(energy(delay.read(1))==0,"Unprepared delay read was not silent");
        delay.push({1,-1});
        for(size_t length:{size_t{4},size_t{17},size_t{36004}}) {
            delay.prepare(length);delay.push({.75f,-.25f});
            const auto edge=delay.read(std::nextafter(1.,2.));
            require(std::abs(edge.l-.75f)<1e-6&&std::abs(edge.r+.25f)<1e-6,"Fractional delay failed just before wrap boundary");
            require(delay.read(std::numeric_limits<double>::quiet_NaN()).l==.75f,"Nonfinite delay age was not handled safely");
            delay.reset();require(energy(delay.read(1))==0,"Delay reset retained old audio");
        }
        for(size_t length:{size_t{4},size_t{17},size_t{256}}) {
            delay.prepare(length);std::vector<Stereo> reference(length);
            for(size_t i=0;i<length*3;++i) {
                const Stereo input{static_cast<float>(i%31)*.03125f,-static_cast<float>(i%23)*.03125f};
                delay.push(input);std::rotate(reference.begin(),reference.begin()+1,reference.end());reference.back()=input;
                for(double age=1;age<=static_cast<double>(length-2);age+=.25) {
                    const auto whole=static_cast<size_t>(std::floor(age));
                    const auto expected=mix(reference[length-whole],reference[length-whole-1],static_cast<float>(age-whole));
                    const auto actual=delay.read(age);
                    require(std::abs(actual.l-expected.l)<1e-6&&std::abs(actual.r-expected.r)<1e-6,"Fractional delay interpolation changed at ring wrap");
                }
            }
        }
    }
    {
        require(sceneDelayRegion(-1)==0&&sceneDelayRegion(7)==3,"Scene delay region endpoints failed");
        for(unsigned region=1;region<4;++region) {
            const float boundary=region*1.75f;
            require(sceneDelayRegion(std::nextafter(boundary,0.f))==region-1&&sceneDelayRegion(boundary)==region,"Scene region boundary rounded into an adjacent region");
        }
        for(unsigned region=0;region<4;++region) {
            const float position=(region+.5f)*7/4;
            require(sceneDelayRegion(position)==region,"Scene Sub1 did not select four regions");
            // Test every published Echo division, including 8 beats at the
            // slowest supported tempo. Detect actual impulse arrival.
            for(int choice=0;choice<9;++choice) {
                SceneProcessor p;p.prepare(8000);SceneSettings s;s.type=1;s.feedback=0;
                s.delayBeats[1]={8,0,6,4};s.delayBeats[1][region]=choice;p.configure(s);
                const size_t expected=static_cast<size_t>(12000*sceneDelayBeats[choice]);size_t onset=0;
                for(size_t i=0;i<=expected+2;++i) {
                    const auto out=p.process(i==0?Stereo{.5f,0}:Stereo{},1,position,0,1,40,i/12000.,0);
                    if(i>0&&onset==0&&std::abs(out.l)>1e-8)onset=i;
                }
                require(onset==expected,"Scene User delay region did not produce the selected beat time");
            }
        }
        // Verify the adapter-independent parameter path and Default/User
        // switching using the actual engine, rather than only Scene settings.
        Engine engine;
        engine.params.set(Param::AutoTempo,0);engine.params.set(Param::Tempo,40);engine.params.set(Param::SceneType,1);engine.params.set(Param::SceneOn,1);
        engine.params.set(Param::SceneDepth,1);engine.params.set(Param::SceneTime,.5f);engine.params.set(Param::SceneResonance,0);
        engine.params.set(Param::EchoDelay1,4);
        for(int user=0;user<2;++user) {
            engine.params.set(Param::UserSettings,static_cast<float>(user));engine.prepare(8000,64);
            std::array<float,64> zero{},left{},right{};
            for(unsigned block=0;block<20;++block)engine.process(zero.data(),zero.data(),left.data(),right.data(),64);
            size_t onset=0;const size_t expected=user?9000:3000;
            for(size_t i=0;i<=expected+2;++i) {
                const float input=i==0?.5f:0;float l{},r{};engine.process(&input,&input,&l,&r,1);
                if(i>0&&onset==0&&std::abs(l)>1e-8)onset=i;
            }
            require(onset==expected,"Engine Default/User delay assignments did not reach DSP");
            require(engine.params.get(Param::EchoDelay1)==4,"Default mode erased a User delay assignment");
        }
        State custom;
        for(const auto group:sceneDelayGroups)for(unsigned region=0;region<4;++region)
            custom.values[static_cast<size_t>(group.first)+region]=static_cast<float>((region+group.scene)%7);
        const auto restored=State::parse(custom.serialize());require(restored.values==custom.values,"Per-effect four-region assignments did not roundtrip");
        const auto old=State::parse("RMX_STATE 1\nparam scene_time 2.625\n");
        require(old.values[static_cast<size_t>(Param::EchoDelay4)]==5,"Old state did not receive default delay assignments");
    }
    for(int type=0;type<10;++type) {
        SceneProcessor processor;processor.prepare(48000);SceneSettings s;s.type=type;processor.configure(s);
        for(size_t i=0;i<24000;++i) {
            const Stereo in{sine(1037,i),sine(7231,i)};
            const auto out=processor.process(in,0,3,.5f,1,120,i/24000.,.2f);
            require(std::abs(out.l-in.l)<1e-6&&std::abs(out.r-in.r)<1e-6,"Scene macro zero is not neutral");
        }
    }
    {
        auto noisePower=[](float sub1,float macro,float sidechain,int wave,int minimum=1) {
            SceneProcessor p;p.prepare(48000);SceneSettings s;s.type=2;s.feedback=0;s.waveform[2]=wave;s.noiseMinimum=minimum;p.configure(s);
            double sum=0;unsigned crossings=0;bool positive=false;std::array<double,4> spectrum{};
            for(size_t i=0;i<96000;++i) {
                const auto out=p.process({},macro,sub1,wave==4?.8f:0,1,120,i/24000.,sidechain);
                if(i>=48000) {
                    sum+=energy(out);const bool next=out.l>0;if(next&&!positive)++crossings;positive=next;
                    spectrum[0]+=out.l*std::cos(2*pi*600*i/48000);spectrum[1]+=out.l*std::sin(2*pi*600*i/48000);
                    spectrum[2]+=out.l*std::cos(2*pi*5000*i/48000);spectrum[3]+=out.l*std::sin(2*pi*5000*i/48000);
                }
            }
            return std::array<double,4>{sum,static_cast<double>(crossings),spectrum[0]*spectrum[0]+spectrum[1]*spectrum[1],spectrum[2]*spectrum[2]+spectrum[3]*spectrum[3]};
        };
        require(noisePower(0,.5f,0,0,0)[0]==0,"Noise User minimum Off does not mute the white-noise source");
        const double factoryMinimum=noisePower(0,.5f,0,0)[0],factoryMaximum=noisePower(7,.5f,0,0)[0];
        require(std::abs(factoryMinimum/factoryMaximum-std::pow(10.,-24./10))<1e-6,"Factory Noise level endpoints differ from measured -18/+6 dB span");
        const auto low=noisePower(7,.2f,0,0),high=noisePower(7,.8f,0,0);
        std::cout<<"Noise low/high cutoff: energy "<<low[0]<<"/"<<high[0]<<", crossings "<<low[1]<<"/"<<high[1]<<", 600:5000 Hz power "<<low[2]/low[3]<<"/"<<high[2]/high[3]<<'\n';
        require(low[0]>1&&low[2]>low[3]*20&&high[3]>high[2]*20,"Noise macro does not sweep the noise filter");
        const auto noDuck=noisePower(7,.5f,0,4)[0],duck=noisePower(7,.5f,.8f,4)[0];
        require(duck<noDuck*.08,"Noise side-chain modulation did not duck the generated source");
    }
    for(const auto [bpm,delay]:std::array<std::pair<double,size_t>,4>{{{120,12000},{90,15984},{128,11232},{137,10488}}}) {
        SceneProcessor p;p.prepare(48000);SceneSettings s;s.type=2;p.configure(s);
        std::vector<Stereo> tail(delay*2);double lr=0,ll=0,rr=0;
        for(size_t i=0;i<48000+tail.size();++i) {
            const auto output=p.process({},128.f/255,128*7.f/255,0,i<48000?1:0,bpm,i*bpm/(60*48000.),0);
            if(i>=24000&&i<48000) {lr+=output.l*output.r;ll+=output.l*output.l;rr+=output.r*output.r;}
            if(i>=48000)tail[i-48000]=output;
        }
        require(std::abs(lr/std::sqrt(ll*rr))<.1,"Factory Noise is not independently excited in stereo");
        for(size_t i=0;i<delay;++i) {
            const auto error=tail[i+delay]-tail[i]*.5f;
            require(peak(error)<1e-7f,"Noise tail does not repeat after half a beat with measured 0.5 feedback");
        }
    }
    {
        for(float cutoff:{0.f,1.f}) {
            SceneProcessor p;p.prepare(48000);SceneSettings s;s.type=1;s.feedback=.55f;p.configure(s);
            size_t onset=0;double first=0,second=0;
            for(size_t i=0;i<43000;++i) {
                const auto out=p.process(i==0?Stereo{.5f,0}:Stereo{},1,4,cutoff,1,120,i/24000.,0);
                require(out.r==0,"Echo leaked a mono impulse into the other channel");
                if(i>0&&onset==0&&std::abs(out.l)>1e-9)onset=i;
                if(i>=18000&&i<24000)first+=energy(out);
                if(i>=36000&&i<42000)second+=energy(out);
            }
            std::cout<<"Echo Sub2 "<<cutoff<<": onset "<<onset<<", repeat energy ratio "<<second/first<<'\n';
            require(onset==18000,"Echo Sub1 did not set the beat delay");
            require(std::abs(second/first-.55*.55)<.002,"Echo Sub2 changed feedback instead of filter cutoff");
        }
    }
    {
        auto response=[](int type,float macro,double hz) {
            SceneProcessor p;p.prepare(48000);SceneSettings s;s.type=type;s.feedback=0;p.configure(s);double sum=0;
            for(size_t i=0;i<48000;++i) {const float in=sine(hz,i);const auto out=p.process({in,in},macro,7,0,1,120,i/24000.,.2f);if(i>=24000)sum+=energy(out);}
            return sum;
        };
        require(response(5,1,19000)>response(5,1,500)*100,"HPF Echo macro does not high-pass the source");
        require(response(6,1,10)>response(6,1,1000)*100,"LPF Echo macro does not low-pass the source");
    }
    {
        // A fully disabled resonance character must not accidentally retain the
        // old generic Sub2-to-feedback mapping or apply an LFO.
        SceneProcessor a,b;a.prepare(48000);b.prepare(48000);SceneSettings s;s.type=2;s.sub2Mode[2]=1;s.resonance[2]=2;a.configure(s);b.configure(s);
        for(size_t i=0;i<48000;++i) {
            auto x=a.process({},.5f,7,0,1,120,i/24000.,0),y=b.process({},.5f,7,1,1,120,i/24000.,0);
            require(x.l==y.l&&x.r==y.r,"None resonance setting still responds to Sub2");
        }
    }
    {
        auto firstReflection=[](int size) {
            SceneProcessor p;p.prepare(48000);SceneSettings s;s.type=4;s.roomSize[0]=size;p.configure(s);
            for(size_t i=0;i<10000;++i) {auto out=p.process(i==0?Stereo{.5f,0}:Stereo{},1,7,0,1,120,i/24000.,0);if(i>10&&energy(out)>1e-12)return i;}
            return size_t{0};
        };
        const auto small=firstReflection(1),large=firstReflection(0);std::cout<<"Reverb first reflection Small/Large: "<<small<<"/"<<large<<" samples\n";
        require(small>500&&large>small*1.5,"Reverb room size did not change reflection timing");
        auto wetPower=[](int type,float sub1,float sub2,double hz) {
            SceneProcessor p;p.prepare(48000);SceneSettings s;s.type=type;p.configure(s);double sum=0;
            for(size_t i=0;i<144000;++i) {const Stereo in{sine(hz,i),sine(hz,i)};auto out=p.process(in,1,sub1,sub2,1,120,i/24000.,.2f);if(type==4)out=out-in;if(i>=96000)sum+=energy(out);}
            return sum;
        };
        require(wetPower(4,0,0,1000)<1e-9,"Reverb Sub1 zero did not remove the reverb send");
        require(wetPower(4,7,1,100)<wetPower(4,7,0,100)*.001,"Reverb Up Sub2 is not a high-pass filter");
        require(wetPower(9,7,1,6000)<wetPower(9,7,0,6000)*.001,"Reverb Down Sub2 is not a low-pass filter");
    }
    {
        auto echoPower=[](int width) {
            SceneProcessor p;p.prepare(8000);SceneSettings s;s.type=1;s.feedback=0;s.width[1]=width;s.delayBeats[1].fill(0);p.configure(s);
            const float sub2=171.f/255;double sum=0;
            for(size_t i=0;i<16000;++i) {
                const float x=.2f*static_cast<float>(std::sin(2*pi*1000*i/8000));
                const auto y=p.process({x,x},1,0,sub2,1,120,i/4000.,0)-Stereo{x,x};if(i>=8000)sum+=energy(y);
            }
            return sum;
        };
        require(echoPower(0)>echoPower(2)*8,"Echo filter width did not change the output response");
        auto reverbPower=[](int filter,double hz) {
            SceneProcessor p;p.prepare(8000);SceneSettings s;s.type=4;s.reverbFilter[0]=filter;p.configure(s);double sum=0;
            for(size_t i=0;i<32000;++i) {
                const float x=.1f*static_cast<float>(std::sin(2*pi*hz*i/8000));const Stereo input{x,x};
                const auto wet=p.process(input,1,7,.5f,1,120,i/4000.,0)-input;if(i>=24000)sum+=energy(wet);
            }
            return sum;
        };
        require(reverbPower(0,60)>reverbPower(2,60)*100,"Reverb low-pass selection did not preserve bass");
        require(reverbPower(2,2200)>reverbPower(0,2200)*100,"Reverb high-pass selection did not preserve treble");
        require(reverbPower(1,60)<reverbPower(0,60)*.1&&reverbPower(1,2200)<reverbPower(2,2200)*.1,"Reverb band-pass selection did not reject both outside bands");
    }
    {
        auto shiftedFrequency=[](int type,float sub2) {
            SceneProcessor p;p.prepare(48000);SceneSettings s;s.type=type;s.feedback=0;p.configure(s);
            unsigned rises=0;bool positive=false;
            for(size_t i=0;i<96000;++i) {const Stereo in{sine(1000,i),sine(1000,i)};auto out=p.process(in,1,3,sub2,1,120,i/24000.,.2f);if(type==3)out=out-in;if(i>=48000) {const bool next=out.l>0;if(next&&!positive)++rises;positive=next;}}
            return rises;
        };
        const auto normal=shiftedFrequency(3,0),up=shiftedFrequency(3,1),down=shiftedFrequency(8,1);
        std::cout<<"Spiral zero/up/down: "<<normal<<"/"<<up<<"/"<<down<<" Hz\n";
        require(normal>=995&&normal<=1005&&up>=1950&&up<=2050&&down>=475&&down<=525,"Spiral Sub2 did not control pitch direction/amount");
    }
    {
        State state;state.values[static_cast<size_t>(Param::SceneTime)]=2.625f;state.values[static_cast<size_t>(Param::BpfWave)]=4;state.values[static_cast<size_t>(Param::ReverbDownRoomSize)]=1;
        auto restored=State::parse(state.serialize());require(restored.values==state.values,"Per-effect Scene settings did not roundtrip");
    }
    for(double rate:{44100.,48000.,96000.}) {
        SceneProcessor processor;processor.prepare(rate);
        for(int type=0;type<10;++type) {
            SceneSettings s;s.type=type;s.feedback=.94f;s.decay=.95f;s.feedbackCharacter.fill(2);s.sub2Mode.fill(1);s.resonance.fill(0);s.noiseMaximum=3;
            processor.configure(s);processor.reset();
            for(size_t i=0;i<static_cast<size_t>(rate);++i) {
                const float a=.2f*static_cast<float>(std::sin(2*pi*737*i/rate));
                const auto out=processor.process({a,-a},1,type==2?7:0,1,1,120,i*2/rate,.2f);
                require(std::isfinite(out.l)&&std::isfinite(out.r)&&std::abs(out.l)<1000&&std::abs(out.r)<1000,"Extreme User Scene settings became unstable");
            }
        }
    }
    std::cout<<"PASS: Scene zero, Noise level/cutoff/side-chain, Echo timing/filter/feedback, source filters, resonance None, reverb controls, Spiral pitch and per-effect state\n";
} catch(const std::exception& e) {std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;} }
