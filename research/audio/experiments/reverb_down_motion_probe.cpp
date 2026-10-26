// Stateful research candidate. Choices are explicit hypotheses, not production defaults.
#include "rmx/Wav.h"
#include "rmx/Dsp.h"
#include "ReverbDownControlCalibration.h"
#include <fstream>
#include <iostream>
#include <sstream>

namespace {
struct Delay {
    std::vector<double> data;
    size_t head{};
    void prepare(size_t maximum){data.assign(maximum+1,0);head=0;}
    void clear() noexcept {std::fill(data.begin(),data.end(),0);head=0;}
    double tap(size_t delay) const noexcept {return data[(head+data.size()-delay)%data.size()];}
    void push(double value) noexcept {data[head]=value;if(++head==data.size())head=0;}
};
struct Filter {
    double b0{},b1{},b2{},a1{},a2{},s1{},s2{};
    void biquad(double hz,bool high) noexcept {
        const double w=2*std::numbers::pi*hz/48000,alpha=std::sin(w)/std::sqrt(2.);
        b0=(1+(high?1:-1)*std::cos(w))/2/(1+alpha);b1=(high?-2:2)*b0;b2=b0;
        a1=-2*std::cos(w)/(1+alpha);a2=(1-alpha)/(1+alpha);
    }
    void onePole(double hz,bool high) noexcept {
        const double t=std::tan(std::numbers::pi*hz/48000),pole=(1-t)/(1+t);
        b0=high?(1+pole)/2:(1-pole)/2;b1=high?-b0:b0;b2=0;a1=-pole;a2=0;
    }
    void clear() noexcept {s1=s2=0;}
    double tick(double x) noexcept {const double y=b0*x+s1;s1=b1*x-a1*y+s2;s2=b2*x-a2*y;return y;}
};
struct AllPass {
    Delay delay;size_t length{};
    void prepare(size_t n){length=n;delay.prepare(n);}
    double tick(double x) noexcept {const double y=delay.tap(length)-.7*x;delay.push(x+.7*y);return y;}
};
struct Controls {int main{128},amount{128},cutoff{},enabled{1};};
// Independently expressed room-size hypothesis, checked against all 2,520
// observable integer delays in the frozen static calibration (raw Main 4..255).
float roomScale(int raw) noexcept {
    const float p=static_cast<float>(std::max(0,raw-3))*(1.f/252.f)*99.f+1.f;
    const float q=p*.02306f+1.01f;
    return (q*q)*.171f+.2f;
}
constexpr std::array<std::array<int,2>,5> roomBases{{{1032,1146},{1060,1856},{1145,1961},{1916,1115},{1992,1190}}};
double mainMix(int raw) noexcept {return std::min(1.,4.*std::max(0,raw-3)/252);}
float dryLevel(int raw) noexcept {
    const float unit=static_cast<float>(std::max(0,raw-3))*(1.f/252.f);
    return unit>.5f?2.f-(unit+unit):1.f;
}
double inputShape(int raw) noexcept {
    const double p=std::min(55.,1+99.*std::max(0,raw-3)/252);
    return .2*(1-.000330578506691*std::pow(p-55,2))+
        .018*std::pow(.1*std::min(0.,p-17),2);
}
double returnShape(int main,int amount) noexcept {
    const double a=amount<100?1:.3+.7*std::pow(1-(amount-100)/155.,2);
    return .7*(a+std::pow(std::min(1.,main/183.),2)*std::pow(1-a,7));
}
struct Event {size_t frame{};std::string control;int value{};};
struct Plan {Controls initial;double tail{};size_t block{128};std::vector<Event> events;};
void valid(const Controls& c) {
    if(c.main<0||c.main>255||c.amount<0||c.amount>255||c.cutoff<0||c.cutoff>255||c.enabled<0||c.enabled>1)
        throw std::runtime_error("Controls outside static raw map");
}
void apply(Controls& c,const Event& e) {
    if(e.control=="main")c.main=e.value;
    else if(e.control=="amount")c.amount=e.value;
    else if(e.control=="cutoff")c.cutoff=e.value;
    else if(e.control=="enabled")c.enabled=e.value;
    else throw std::runtime_error("Unknown event control");
    valid(c);
}
Plan readPlan(const std::filesystem::path& path) {
    std::ifstream f(path);std::string text;Plan plan;size_t line=0;Controls test;bool blockSeen=false;
    if(!f)throw std::runtime_error("Cannot open motion schedule");
    while(std::getline(f,text)) {
        std::istringstream row(text);std::string kind,extra;row>>kind;
        if(line==0) {int version{};if(kind!="RMX_REVERB_MOTION"||!(row>>version)||version!=1)throw std::runtime_error("Invalid motion schema");}
        else if(line==1) {
            if(kind!="initial"||!(row>>plan.initial.main>>plan.initial.amount>>plan.initial.cutoff>>plan.initial.enabled))
                throw std::runtime_error("Invalid initial controls");
            valid(plan.initial);test=plan.initial;
        } else if(line==2) {
            if(kind!="tail"||!(row>>plan.tail)||!std::isfinite(plan.tail)||plan.tail<0||plan.tail>120)
                throw std::runtime_error("Invalid tail");
        } else {
            if(kind=="block"){
                if(blockSeen||!(row>>plan.block)||plan.block<8||plan.block>4096||!plan.events.empty())
                    throw std::runtime_error("Invalid callback block size");
                blockSeen=true;
                if(row>>extra)throw std::runtime_error("Unexpected callback field");
                ++line;continue;
            }
            int64_t frame{};Event e;
            if(kind!="event"||!(row>>frame>>e.control>>e.value)||frame<0)
                throw std::runtime_error("Invalid event");
            e.frame=static_cast<size_t>(frame);
            if(!plan.events.empty()&&e.frame<plan.events.back().frame)throw std::runtime_error("Events must be ordered");
            apply(test,e);plan.events.push_back(std::move(e));
        }
        if(row>>extra)throw std::runtime_error("Unexpected schedule field");
        ++line;
    }
    if(line<3)throw std::runtime_error("Incomplete motion schedule");
    return plan;
}
class Model {
public:
    Model(std::string gateMode,std::string cutoffPosition,bool gainAtInput,std::string levelPosition,size_t rampFrames,std::string rampComponents,double decaySlewStep):gate(std::move(gateMode)),position(std::move(cutoffPosition)),level(std::move(levelPosition)),rampParts(rampComponents=="adaptive"||rampComponents=="startup"?"staged":rampComponents),writeGain(gainAtInput),rampLength(rampFrames),decaySlew(decaySlewStep),adaptive(rampComponents=="adaptive"||rampComponents=="startup"),startup(rampComponents=="startup") {
        for(size_t j=0;j<5;++j)for(size_t ch=0;ch<2;++ch) {
            size_t maximum=1;
            for(const auto& row:reverbDownControls)maximum=std::max(maximum,static_cast<size_t>(row.delays[j][ch]));
            combs[j][ch].prepare(maximum);
        }
        for(auto& chain:inputFilters){chain[0].onePole(80,true);chain[1].onePole(10000,false);chain[2].biquad(54,true);}
        for(auto& filter:outputHigh)filter.biquad(54,true);
        allpasses[0][0].prepare(335);allpasses[0][1].prepare(1091);
        allpasses[1][0].prepare(395);allpasses[1][1].prepare(1031);
    }
    void control(const Controls& target) noexcept {
        const auto approach=[](int a,int b){return a+(a<b?1:(a>b?-1:0));};
        Controls c=state;
        c.main=approach(c.main,target.main);c.cutoff=approach(c.cutoff,target.cutoff);c.enabled=target.enabled;
        // Selection reaches the room one block after the input command. The
        // current controls at that point initialize its formerly inactive state.
        if(startup&&!everActivated&&audioBlock[blockHead].enabled){
            c=target;slowMain=pendingMain=c.main;mainPeriod=60;
            sharedBlocks=geometryRemaining=mixRemaining=0;stagedRemaining.fill(0);steps.fill(0);prepared=false;
        }
        geometryStart=amountStart=false;
        if(!sharedBlocks){
            if(slowMain!=target.main){
                const int desired=15-std::min(5,std::abs(target.main-slowMain));
                mainPeriod=approach(mainPeriod,desired);
                pendingMain=approach(slowMain,target.main);
                sharedBlocks=static_cast<size_t>(mainPeriod);geometryStart=true;
            }else if(c.amount!=target.amount){
                c.amount=approach(c.amount,target.amount);sharedBlocks=5;amountStart=true;
            }
        }
        configure(c);
    }
    void configure(const Controls& c) noexcept {
        if(adaptive&&!prepared){slowMain=pendingMain=c.main;fastMix=mainMix(c.main);}
        const int roomMain=adaptive?(geometryStart?pendingMain:slowMain):c.main;
        const auto& row=reverbDownControls[static_cast<size_t>(roomMain)];
        if(!adaptive)delays=row.delays;
        else if(!prepared||geometryStart){
            const float scale=roomScale(roomMain);
            for(size_t j=0;j<5;++j)for(size_t ch=0;ch<2;++ch){
                const float requested=scale*static_cast<float>(roomBases[j][ch]);
                delayTarget[j][ch]=requested;
                if(!prepared)delayCurrent[j][ch]=requested;
                delayStep[j][ch]=sharedBlocks?(requested-delayCurrent[j][ch])*(1.f/static_cast<float>(sharedBlocks*32)):0;
                delays[j][ch]=static_cast<int>(delayCurrent[j][ch]);
            }
            geometryRemaining=sharedBlocks*32;
        }
        const auto decay=[](double raw){return 1+49*std::pow(std::max(0.,raw-3)/252,3);};
        decayTarget=decay(c.amount);
        if(!prepared||!decaySlew)decayCurrent=decayTarget;
        const double effectiveDecay=adaptive&&geometryStart&&c.main<=3?std::min(8.,decayCurrent):decayCurrent;
        const double exponent=decay(128)/effectiveDecay;
        for(size_t j=0;j<5;++j){
            const auto& feedbackRow=adaptive&&roomMain<4?reverbDownControls[4]:row;
            const double hiddenScale=adaptive&&roomMain<4?roomScale(roomMain)/roomScale(4):1;
            gl[j]=std::pow(feedbackRow.gainL[j],exponent*hiddenScale);
            gr[j]=std::pow(feedbackRow.gainR[j],exponent*hiddenScale);
        }
        wetGain=row.wetGain*reverbDownAmountGain[static_cast<size_t>(c.amount)]/reverbDownAmountGain[128];
        wetGain*=1+reverbDownMainCorrection[static_cast<size_t>(roomMain)]*reverbDownAmountCorrection[static_cast<size_t>(c.amount)];
        sendGain=wetGain;returnGain=1;
        if(level=="output"){sendGain=1;returnGain=wetGain;}
        else if(level=="main-send"){
            sendGain=row.wetGain;
            returnGain=reverbDownAmountGain[static_cast<size_t>(c.amount)]/reverbDownAmountGain[128];
            returnGain*=1+reverbDownMainCorrection[static_cast<size_t>(c.main)]*reverbDownAmountCorrection[static_cast<size_t>(c.amount)];
        } else if(level=="amount-send"){
            sendGain=reverbDownAmountGain[static_cast<size_t>(c.amount)]/reverbDownAmountGain[128];
            returnGain=row.wetGain*(1+reverbDownMainCorrection[static_cast<size_t>(c.main)]*reverbDownAmountCorrection[static_cast<size_t>(c.amount)]);
        }
        if(adaptive){
            // Factor the independently measured static gain into input size
            // compensation and return normalization; no motion fitting here.
            const int audibleMain=std::max(4,slowMain);
            const double staticMain=reverbDownControls[static_cast<size_t>(audibleMain)].wetGain;
            sendGain=staticMain/(mainMix(audibleMain)*returnShape(audibleMain,128));
            if(slowMain<4)sendGain*=inputShape(slowMain)/inputShape(4);
            const int targetAudible=std::max(4,roomMain);
            const double targetSend=reverbDownControls[static_cast<size_t>(targetAudible)].wetGain/
                (mainMix(targetAudible)*returnShape(targetAudible,128));
            returnGain=roomMain<4?returnShape(roomMain,c.amount):wetGain/(targetSend*mainMix(roomMain));
            if(!prepared)fastMix=mainMix(c.main);
            if(c.main!=state.main){fastMixTarget=mainMix(c.main);fastMixStep=(fastMixTarget-fastMix)/32;mixRemaining=32;}
        }
        std::array<double,12> requested{};
        for(size_t j=0;j<5;++j){requested[j]=gl[j];requested[j+5]=gr[j];}
        requested[10]=sendGain;requested[11]=returnGain;
        if(!prepared||(rampParts!="staged"&&!rampLength)){coefficients=targetCoefficients=requested;remaining=0;prepared=true;}
        else if(rampParts=="staged"){
            for(size_t j=0;j<12;++j)if(requested[j]!=targetCoefficients[j]){
                const size_t length=adaptive?(j==10?1:(geometryStart?(j<10?sharedBlocks*32:160):
                    (j<10?160:static_cast<size_t>(c.amount<state.amount?2000:2600)*32))):
                    (j<10?160:static_cast<size_t>(c.amount<state.amount?2000:2600)*32);
                if(adaptive&&j!=10&&!geometryStart&&!amountStart)continue;
                targetCoefficients[j]=requested[j];stagedRemaining[j]=length;
                steps[j]=(requested[j]-coefficients[j])/static_cast<double>(length);
            }
        }
        else if(requested!=targetCoefficients){
            targetCoefficients=requested;remaining=rampLength;
            for(size_t j=0;j<12;++j){
                const bool smooth=rampParts=="all"||(rampParts=="levels"?j>=10:j<10);
                if(smooth)steps[j]=(requested[j]-coefficients[j])/static_cast<double>(rampLength);
                else {coefficients[j]=requested[j];steps[j]=0;}
            }
        }
        compensation=1+.5*c.cutoff/255;
        dryGain=startup?dryLevel(c.main):reverbDownControls[static_cast<size_t>(c.main)].dryGain;
        if(gate=="faded"){
            if(!activationPrepared){
                initialActive=c.enabled;
                inputFade=c.enabled?1.f:0.f;
                dryCurrent=static_cast<float>(c.enabled&&!startup?dryGain:1);
                dryTarget=dryCurrent;activationPrepared=true;
            } else if(c.main!=state.main&&lastDelayedEnabled){
                setDry(static_cast<float>(dryGain),32);
            }
        }
        const double hz=17330*std::pow(261./17330,std::max(0.,static_cast<double>(c.cutoff)-4)/251);
        for(auto& filter:outputFilter)filter.biquad(hz,false);
        if(gate=="reset"&&c.enabled!=state.enabled)clear();
        state=c;
    }
    std::array<rmx::Stereo,2> tick(rmx::Stereo input) noexcept {
        if(adaptive){
            if(geometryRemaining){
                for(size_t j=0;j<5;++j)for(size_t ch=0;ch<2;++ch){
                    delays[j][ch]=static_cast<int>(delayCurrent[j][ch]);
                }
            }
            if(mixRemaining){fastMix+=fastMixStep;if(!--mixRemaining)fastMix=fastMixTarget;}
            if(frame%32==31&&sharedBlocks&&!--sharedBlocks)slowMain=pendingMain;
        }
        if(rampParts=="staged")for(size_t j=0;j<12;++j)if(stagedRemaining[j]){
            // Startup advances the ramp clock but leaves feedback state still;
            // reaching the endpoint commits its target even while muted.
            if(j>=10||!warmRemaining)coefficients[j]+=steps[j];
            if(!--stagedRemaining[j])coefficients[j]=targetCoefficients[j];
        }
        if(decaySlew&&frame%32==0&&decayCurrent!=decayTarget){
            const double difference=decayTarget-decayCurrent;
            decayCurrent+=std::clamp(difference,-decaySlew,decaySlew);
            const auto& row=reverbDownControls[static_cast<size_t>(state.main)];
            const double neutral=1+49*std::pow(125./252,3),exponent=neutral/decayCurrent;
            for(size_t j=0;j<5;++j){
                coefficients[j]=targetCoefficients[j]=std::pow(row.gainL[j],exponent);
                coefficients[j+5]=targetCoefficients[j+5]=std::pow(row.gainR[j],exponent);
                steps[j]=steps[j+5]=0;
            }
        }
        ++frame;
        float routing=1;
        if(startup&&frame<=160){startupFade+=.00625f;routing=startupFade;}
        if(remaining){
            for(size_t j=0;j<12;++j)coefficients[j]+=steps[j];
            if(!--remaining)coefficients=targetCoefficients;
        }
        const bool feed=state.enabled||gate=="output";
        const bool emit=state.enabled||gate=="inlet"||gate=="faded";
        const rmx::Stereo routed=startup?rmx::Stereo{
            static_cast<float>(static_cast<float>(input.l*routing)*routing),
            static_cast<float>(static_cast<float>(input.r*routing)*routing)}:input;
        std::array<double,2> source{routed.l,routed.r},wet{};
        if(gate=="faded"){
            inputFade=std::clamp(inputFade+(state.enabled?.00625f:-.00625f),0.f,1.f);
            for(auto& value:source)value*=inputFade;
        }
        for(size_t ch=0;!adaptive&&ch<2;++ch) {
            for(size_t j=0;j<(gate=="faded"?2:3);++j)source[ch]=inputFilters[ch][j].tick(source[ch]);
        }
        // The original has one 32-frame audio block of latency. Button gating
        // acts on new input; knobs act on the already buffered audio.
        const auto delayed=audioBlock[blockHead];
        const auto gated=(feed||gate=="faded")?source:std::array<double,2>{};
        audioBlock[blockHead]={routed,gated,startup&&frame<=32?0:state.enabled};
        if(++blockHead==audioBlock.size())blockHead=0;
        source=delayed.source;
        if(gate=="faded"){
            if(delayed.enabled!=lastDelayedEnabled){
                lastDelayedEnabled=delayed.enabled;
                setDry(static_cast<float>(delayed.enabled?dryGain:1),160);
                if(delayed.enabled&&!everActivated){
                    everActivated=true;warmRemaining=12416+(initialActive&&!startup?32:0);dryRestart=frame+32;
                }
            }
            if(dryRestart&&frame==dryRestart){setDry(dryTarget,160);dryRestart=0;}
            if(dryRemaining){dryCurrent+=dryStep;--dryRemaining;}
        }
        const bool warming=gate=="faded"&&warmRemaining;
        for(size_t ch=0;ch<2;++ch) {
            source[ch]*=coefficients[10]*(adaptive?fastMix:1);
            if(adaptive)for(size_t j=0;j<2;++j)source[ch]=inputFilters[ch][j].tick(source[ch]);
            if(position=="pre")source[ch]=outputFilter[ch].tick(source[ch]);
        }
        for(size_t j=0;j<5;++j) {
            const double left=warming?0:combs[j][0].tap(static_cast<size_t>(delays[j][0]))*(writeGain?1:coefficients[j]);
            const double right=warming?0:combs[j][1].tap(static_cast<size_t>(delays[j][1]))*(writeGain?1:coefficients[j+5]);
            combs[j][0].push((source[0]+right)*(!warming&&writeGain?coefficients[j]:1));
            combs[j][1].push(warming&&j==0?0:(source[1]+left)*(!warming&&writeGain?coefficients[j+5]:1));
            wet[0]+=left;wet[1]+=right;
        }
        if(adaptive&&geometryRemaining){
            for(size_t j=0;j<5;++j)for(size_t ch=0;ch<2;++ch){
                // As with feedback, moving reads begin after startup unmuting.
                if(!warming)delayCurrent[j][ch]+=delayStep[j][ch];
                if(geometryRemaining==1)delayCurrent[j][ch]=delayTarget[j][ch];
                delays[j][ch]=static_cast<int>(delayCurrent[j][ch]);
            }
            --geometryRemaining;
        }
        for(size_t ch=0;ch<2;++ch) {
            if(position=="comb")wet[ch]=outputFilter[ch].tick(wet[ch])*compensation;
            for(auto& ap:allpasses[ch])wet[ch]=ap.tick(wet[ch]);
            if(gate=="faded")wet[ch]=outputHigh[ch].tick(wet[ch]);
            if(position=="post")wet[ch]=outputFilter[ch].tick(wet[ch]);
            wet[ch]*=coefficients[11];
        }
        if(warming)--warmRemaining;
        const double direct=gate=="faded"?dryCurrent:(delayed.enabled?dryGain:1);
        const rmx::Stereo dry{static_cast<float>(delayed.input.l*direct),static_cast<float>(delayed.input.r*direct)};
        const rmx::Stereo output{static_cast<float>(delayed.input.l*direct+(emit?(position=="comb"?1:compensation)*wet[0]:0)),
                                 static_cast<float>(delayed.input.r*direct+(emit?(position=="comb"?1:compensation)*wet[1]:0))};
        if(gate=="faded"&&!dryRemaining){dryCurrent=dryTarget;dryStep=0;}
        return {output,dry};
    }
private:
    void setDry(float target,size_t length) noexcept {
        dryTarget=target;dryRemaining=length;
        dryStep=startup?(target-dryCurrent)*(1.f/static_cast<float>(length)):(target-dryCurrent)/static_cast<float>(length);
    }
    void clear() noexcept {
        for(auto& pair:combs)for(auto& delay:pair)delay.clear();
        for(auto& chain:allpasses)for(auto& ap:chain)ap.delay.clear();
        for(auto& chain:inputFilters)for(auto& filter:chain)filter.clear();
        for(auto& filter:outputFilter)filter.clear();
        for(auto& filter:outputHigh)filter.clear();
    }
    std::array<std::array<Delay,2>,5> combs;
    std::array<std::array<AllPass,2>,2> allpasses;
    std::array<std::array<Filter,3>,2> inputFilters;
    std::array<Filter,2> outputFilter;
    std::array<Filter,2> outputHigh;
    std::array<std::array<int,2>,5> delays{};
    std::array<double,5> gl{},gr{};
    std::array<double,12> coefficients{},targetCoefficients{},steps{};
    std::array<size_t,12> stagedRemaining{};
    bool prepared{};
    Controls state;
    struct BufferedInput {rmx::Stereo input{};std::array<double,2> source{};int enabled{};};
    std::array<BufferedInput,32> audioBlock{};
    size_t blockHead{};
    double wetGain{},sendGain{},returnGain{1},dryGain{1},compensation{1};
    std::string gate,position,level,rampParts;bool writeGain{};
    size_t rampLength{},remaining{};
    size_t frame{};
    double decaySlew{},decayCurrent{},decayTarget{};
    float inputFade{},dryCurrent{1},dryTarget{1},dryStep{};
    size_t warmRemaining{},dryRemaining{},dryRestart{};
    bool activationPrepared{},lastDelayedEnabled{},everActivated{},initialActive{};
    bool adaptive{},geometryStart{},amountStart{},startup{};
    float startupFade{};
    int slowMain{},pendingMain{},mainPeriod{60};
    size_t sharedBlocks{},geometryRemaining{},mixRemaining{};
    std::array<std::array<float,2>,5> delayCurrent{},delayTarget{},delayStep{};
    double fastMix{},fastMixTarget{},fastMixStep{};
};

// Input collection and output draining have independent cursors. A partial
// callback may drain a whole output block after collecting fewer input frames.
// Pending output starts empty; untouched callback positions retain raw input.
// The processed stream supplied here already includes its normal 32-frame FIFO,
// so index +32 addresses a DSP block without adding a second buffering delay.
void callbacks(rmx::Sample& output,rmx::Sample& dry,const rmx::Sample& input,const Plan& plan,size_t extent){
    const auto processed=output.frames,processedDry=dry.frames;
    std::array<rmx::Stereo,32> pending{},pendingDry{};
    size_t collected=0,available=0,processedFrame=0,event=0;
    for(size_t start=0;start<extent;){
        while(event<plan.events.size()&&plan.events[event].frame<=start)++event;
        size_t count=std::min(plan.block,extent-start);
        if(event<plan.events.size())count=std::min(count,plan.events[event].frame-start);
        for(size_t i=0;i<count;++i)output.frames[start+i]=dry.frames[start+i]=start+i<input.frames.size()?input.frames[start+i]:rmx::Stereo{};
        size_t received=0,written=0;
        while(received<count){
            const auto take=std::min(32-collected,count-received);collected+=take;received+=take;
            const auto emit=std::min(available,count-written);
            for(size_t i=0;i<emit;++i){output.frames[start+written+i]=pending[i];dry.frames[start+written+i]=pendingDry[i];}
            written+=emit;available-=emit;
            for(size_t i=0;i<available;++i){pending[i]=pending[i+emit];pendingDry[i]=pendingDry[i+emit];}
            if(collected==32){
                for(size_t i=0;i<32;++i){
                    const auto at=processedFrame+32+i;
                    pending[i]=at<processed.size()?processed[at]:rmx::Stereo{};
                    pendingDry[i]=at<processedDry.size()?processedDry[at]:rmx::Stereo{};
                }
                processedFrame+=32;collected=0;available=32;
            }
        }
        start+=count;
    }
    output.frames.resize(extent);dry.frames.resize(extent);
}
}
int main(int argc,char** argv){try {
    if(argc<9||argc>13)throw std::runtime_error("Usage: reverb_down_motion_probe INPUT NEW_OUTPUT SCHEDULE inlet|output|inlet-output|reset|faded pre|comb|post read|write CONTROL_QUANTUM NEW_DRY_TRACE [send|output|main-send|amount-send [COEFFICIENT_RAMP_FRAMES [all|levels|feedback|staged|adaptive|startup [DECAY_STEP_PER_32_FRAMES]]]]");
    if(std::filesystem::exists(argv[2])||std::filesystem::exists(argv[8]))throw std::runtime_error("Output/trace must be new");
    const std::string gate=argv[4],position=argv[5],gain=argv[6];
    if(gate!="inlet"&&gate!="output"&&gate!="inlet-output"&&gate!="reset"&&gate!="faded")throw std::runtime_error("Invalid gate mode");
    if(position!="pre"&&position!="comb"&&position!="post")throw std::runtime_error("Invalid cutoff position");
    if(gain!="read"&&gain!="write")throw std::runtime_error("Invalid gain position");
    const std::string level=argc>=10?argv[9]:"send";
    if(level!="send"&&level!="output"&&level!="main-send"&&level!="amount-send")throw std::runtime_error("Invalid level position");
    size_t ramp{};
    if(argc>=11){const std::string value=argv[10];size_t count{};ramp=std::stoul(value,&count);if(count!=value.size()||ramp>200000)throw std::runtime_error("Invalid coefficient ramp");}
    const std::string parts=argc>=12?argv[11]:"all";
    if(parts!="all"&&parts!="levels"&&parts!="feedback"&&parts!="staged"&&parts!="adaptive"&&parts!="startup")throw std::runtime_error("Invalid ramp components");
    double decaySlew{};
    if(argc==13){const std::string value=argv[12];size_t count{};decaySlew=std::stod(value,&count);if(count!=value.size()||!std::isfinite(decaySlew)||decaySlew<0||decaySlew>50||(decaySlew&&parts!="levels"))throw std::runtime_error("Invalid decay slew");}
    const std::string quantumText=argv[7];size_t used{};const auto quantum=std::stoul(quantumText,&used);
    if(used!=quantumText.size()||(quantum!=1&&quantum!=32&&quantum!=128))throw std::runtime_error("Invalid control quantum");
    if((parts=="staged"||parts=="adaptive"||parts=="startup")&&(quantum!=32||ramp))throw std::runtime_error("Staged controller requires quantum 32 and no generic coefficient ramp");
    if((parts=="adaptive"||parts=="startup")&&(gate!="faded"||position!="post"||gain!="read"||level!="output"))
        throw std::runtime_error("Adaptive research controller requires faded/post/read/output");
    const auto plan=readPlan(argv[3]);const auto input=rmx::readWav(argv[1],180);
    if(input.rate!=48000)throw std::runtime_error("Research candidate requires 48 kHz");
    rmx::Sample output,dry;output.rate=dry.rate=48000;
    const size_t extent=input.frames.size()+static_cast<size_t>(std::llround(plan.tail*48000));
    output.frames.resize(extent+(parts=="startup"?32:0));dry.frames.resize(output.frames.size());
    for(const auto& e:plan.events)if(e.frame>=extent)throw std::runtime_error("Event outside render extent");
    Model model(gate,position,gain=="write",level,ramp,parts,decaySlew);Controls target=plan.initial,current=plan.initial;model.configure(current);size_t event=0,amountWait=0;bool dirty=false;
    for(size_t n=0;n<output.frames.size();++n) {
        if((parts=="adaptive"||parts=="startup")&&n%32==0&&n)model.control(target);
        if(gate!="faded")while(event<plan.events.size()&&plan.events[event].frame==n){apply(target,plan.events[event]);++event;dirty=true;}
        const bool amountReady=amountWait==0;
        if(n%quantum==0&&amountWait)--amountWait;
        if(parts!="adaptive"&&parts!="startup"&&dirty&&n%quantum==0){
            const auto approach=[](int a,int b){return a+(a<b?1:(a>b?-1:0));};
            current.main=approach(current.main,target.main);
            if(parts!="staged"||amountReady){
                if(parts=="staged"&&current.amount!=target.amount)amountWait=4;
                current.amount=approach(current.amount,target.amount);
            }
            current.cutoff=approach(current.cutoff,target.cutoff);
            current.enabled=target.enabled;
            model.configure(current);
            dirty=current.main!=target.main||current.amount!=target.amount||current.cutoff!=target.cutoff;
        }
        if(gate=="faded")while(event<plan.events.size()&&plan.events[event].frame==n){apply(target,plan.events[event]);++event;dirty=true;}
        const auto result=model.tick(n<input.frames.size()?input.frames[n]:rmx::Stereo{});
        output.frames[n]=result[0];dry.frames[n]=result[1];
    }
    if(parts=="startup")callbacks(output,dry,input,plan,extent);
    rmx::writeWav(argv[2],output);rmx::writeWav(argv[8],dry);
    std::cout<<"Rendered stateful Down research hypothesis\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
