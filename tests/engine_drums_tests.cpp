#include "rmx/Engine.h"
#include "rmx/FixedArena.h"
#include <cstdlib>
#include <iostream>
#include <memory>
#include <new>
#include <stdexcept>
namespace {
thread_local bool tracking=false;thread_local size_t allocations=0;
void require(bool value,const char* text){if(!value)throw std::runtime_error(text);}
void* allocate(size_t n,size_t alignment){if(tracking)++allocations;void* p=nullptr;if(alignment<=alignof(std::max_align_t))p=std::malloc(n?n:1);else if(posix_memalign(&p,alignment,n?n:alignment)!=0)p=nullptr;if(!p)throw std::bad_alloc();return p;}
void setup(rmx::Engine& engine,bool protect=false){engine.setOutputProtection(protect);engine.params.set(rmx::Param::AutoTempo,0);engine.params.set(rmx::Param::Quantize,0);engine.params.set(rmx::Param::SceneType,1);engine.prepare(48000,256);}
}
void* operator new(size_t n){return allocate(n,alignof(std::max_align_t));}
void* operator new[](size_t n){return ::operator new(n);}
void* operator new(size_t n,std::align_val_t a){return allocate(n,static_cast<size_t>(a));}
void operator delete(void* p)noexcept{std::free(p);}void operator delete[](void* p)noexcept{std::free(p);}
void operator delete(void* p,std::align_val_t)noexcept{std::free(p);}
int main(){try{
    constexpr size_t bytes=64*1024*1024;auto memory=std::make_unique<std::byte[]>(bytes);rmx::FixedArena arena(memory.get(),bytes);
    auto* old=std::pmr::set_default_resource(&arena);struct Restore{std::pmr::memory_resource* p;~Restore(){std::pmr::set_default_resource(p);}}restore{old};
    {
        rmx::Engine event,split;setup(event);setup(split);std::array<float,256> a{},b{},x{},y{};
        event.process(nullptr,nullptr,a.data(),b.data(),256);split.process(nullptr,nullptr,x.data(),y.data(),256);
        for(unsigned pad=0;pad<4;++pad){
            const rmx::Event hit{rmx::EventType::Trigger,static_cast<uint8_t>(pad),.7f,37,0,0};
            event.process(nullptr,nullptr,a.data(),b.data(),128,{},std::span{&hit,1});
            split.process(nullptr,nullptr,x.data(),y.data(),37);auto queued=hit;queued.offset=0;split.enqueue(queued);
            split.process(nullptr,nullptr,x.data()+37,y.data()+37,91);
            for(size_t i=0;i<128;++i)require(a[i]==x[i]&&b[i]==y[i],"Internal drum event offset differs from explicit callback split");
        }
        event.params.set(rmx::Param::Overdub,1);
        const auto before=arena.allocations();tracking=true;
        for(unsigned block=0;block<200;++block){
            const rmx::Event hit{rmx::EventType::Trigger,static_cast<uint8_t>(block%4),.5f,13,0,0};
            event.process(nullptr,nullptr,a.data(),b.data(),128,{},std::span{&hit,1});
        }
        const rmx::Event panic{rmx::EventType::Panic,0,1,17};event.process(nullptr,nullptr,a.data(),b.data(),128,{},std::span{&panic,1});
        for(size_t i=17;i<128;++i)require(a[i]==0&&b[i]==0,"Panic left a native factory voice playing");
        event.reset();require(allocations==0&&arena.allocations()==before,"Factory drum callback/event/reset allocated");tracking=false;
    }
    {
        // A processed block generated before Panic is already on the common
        // clock. During the Scene-off ramp it is not an unprocessed pad stem;
        // subtracting the full pad invents an inverted transient.
        rmx::Engine stopped,control;
        for(auto* engine:{&stopped,&control}){
            engine->setOutputProtection(false);engine->params.set(rmx::Param::AutoTempo,0);engine->params.set(rmx::Param::Quantize,0);
            engine->params.set(rmx::Param::SceneType,5);engine->params.set(rmx::Param::SceneSource,1);
            engine->params.set(rmx::Param::SceneOn,1);engine->params.set(rmx::Param::SceneDepth,1);
            engine->prepare(48000,32);
        }
        std::array<float,32> a{},b{},x{},y{};
        for(unsigned block=0;block<64;++block){stopped.process(nullptr,nullptr,a.data(),b.data(),32);control.process(nullptr,nullptr,x.data(),y.data(),32);}
        for(auto* engine:{&stopped,&control})engine->enqueue({rmx::EventType::Trigger,0,1,0,0,0});
        for(unsigned block=0;block<20;++block){stopped.process(nullptr,nullptr,a.data(),b.data(),32);control.process(nullptr,nullptr,x.data(),y.data(),32);}
        for(auto* engine:{&stopped,&control})engine->params.set(rmx::Param::SceneOn,0);
        stopped.process(nullptr,nullptr,a.data(),b.data(),32);control.process(nullptr,nullptr,x.data(),y.data(),32);
        stopped.enqueue({rmx::EventType::Panic});
        stopped.process(nullptr,nullptr,a.data(),b.data(),32);control.process(nullptr,nullptr,x.data(),y.data(),32);
        float peak=0;for(size_t i=0;i<32;++i){peak=std::max(peak,std::abs(x[i]));require(a[i]==x[i]&&b[i]==y[i],"Panic subtracted an unprocessed pad from queued Scene audio");}
        require(peak>1e-5f,"Queued Scene-off guard did not exercise nonzero audio");
    }
    for(unsigned mode=0;mode<3;++mode){
        // Hosts restore normalized controls after prepare. Source selectors
        // and master bypass must start at the restored values, just like
        // controls supplied before prepare, rather than fading stale defaults.
        rmx::Engine configured,restored;
        auto configure=[mode](rmx::Engine& engine){
            engine.setOutputProtection(false);engine.params.set(rmx::Param::AutoTempo,0);engine.params.set(rmx::Param::Quantize,0);
            engine.params.set(rmx::Param::SceneType,5);engine.params.set(rmx::Param::SceneSource,1);
            engine.params.set(rmx::Param::SceneOn,mode==2?0:1);engine.params.set(rmx::Param::SceneDepth,151/255.f);
            engine.params.set(rmx::Param::IsolateSource,1);engine.params.set(rmx::Param::IsolateOn,mode==2?1:0);
            engine.params.set(rmx::Param::Low,mode==2?-1:0);engine.params.set(rmx::Param::Mid,mode==2?-1:0);engine.params.set(rmx::Param::High,mode==2?-1:0);
            engine.params.set(rmx::Param::Bypass,mode==1?1:0);
        };
        configure(configured);configured.prepare(48000,64);restored.prepare(48000,64);configure(restored);
        std::array<float,64> left{},right{},a{},b{},x{},y{};
        const rmx::Event hit{rmx::EventType::Trigger,static_cast<uint8_t>(mode),.7f,17,0,0};
        for(unsigned block=0;block<16;++block){
            for(size_t i=0;i<64;++i){left[i]=.013f*std::sin(static_cast<float>(block*64+i)*.11f);right[i]=-.008f*std::cos(static_cast<float>(block*64+i)*.07f);}
            const auto events=block?std::span<const rmx::Event>{}:std::span<const rmx::Event>{&hit,1};
            configured.process(left.data(),right.data(),a.data(),b.data(),64,{},events);restored.process(left.data(),right.data(),x.data(),y.data(),64,{},events);
            for(size_t i=0;i<64;++i)require(a[i]==x[i]&&b[i]==y[i],"Restored source selectors or bypass differ from pre-prepare controls");
        }
    }
    {
        // Original one-beat kick intervals retain the first voice until the next
        // trigger, then fade160 frames before restarting. A tiny tail error
        // must not turn that second hit into an immediate restart.
        rmx::Engine engine;engine.params.set(rmx::Param::XRoll,5);setup(engine);
        std::array<float,256> left{},right{};
        for(unsigned block=0;block<4;++block)engine.process(nullptr,nullptr,left.data(),right.data(),256);
        engine.enqueue({rmx::EventType::Trigger,0});
        std::vector<float> audio(24576);
        for(size_t at=0;at<audio.size();at+=256){
            const rmx::Event repeat{rmx::EventType::Trigger,0,1,192,0,0};
            const auto events=at==23808?std::span<const rmx::Event>{&repeat,1}:std::span<const rmx::Event>{};
            engine.process(nullptr,nullptr,left.data(),right.data(),256,{},events);std::copy(left.begin(),left.end(),audio.begin()+static_cast<std::ptrdiff_t>(at));
        }
        float peak=0;
        for(size_t i=0;i<32;++i){peak=std::max(peak,std::abs(audio[48+i]));require(audio[48+i]==audio[24208+i],"One-beat kick roll lost the reference160-frame retrigger fade");}
        require(peak>1e-5f,"One-beat kick timing guard did not exercise nonzero audio");
    }
    {
        rmx::FactoryRollClock clock;
        require(!clock.start(0,.25),"Factory roll started without selecting a drum");
        std::vector<unsigned> frames;
        for(unsigned frame=0;frame<=48000;frame+=32){
            if(frame==32){clock.select(0);require(clock.start(0,.25),"Selected factory roll did not start");}
            if(clock.advance(120))frames.push_back(frame);
        }
        require(frames==std::vector<unsigned>{6016,12000,18016,24032,30016,36000,42016,48000},"Factory roll clock differs from original cold-quarter boundary observations");
        clock.stop();require(!clock.start(0,.25),"Factory roll remained armed after release");
        clock.select(1);require(!clock.start(1,.25),"Selecting a drum rearmed a released strip position");
        clock.position();require(clock.start(1,.25),"Repeated strip position did not rearm the roll");
        clock.stop();clock.position();require(clock.start(1,.25),"Release discarded the prior drum selection");
    }
    {
        rmx::FactoryRollClock clock;
        clock.setHold(true);clock.position();
        for(unsigned i=0;i<40;++i)require(!clock.advance(120),"Unselected Hold emitted a drum");
        clock.select(2);require(clock.selectOnly(),"Initial Hold lost its silent running clock");
        clock.release();require(clock.active(),"Physical release cancelled latched Hold");
        clock.setHold(false);require(!clock.active(),"Hold-off did not stop a released strip");
        clock.position();require(clock.start(2,.25),"Position write did not rearm released Hold");
        clock.setHold(true);clock.setHold(false);require(clock.active(),"Hold-off cancelled a physical touch");
        clock.release();require(!clock.active(),"Touch release left an unheld roll running");
    }
    {
        rmx::FactoryRollClock clock;clock.beginCallback(true,0,32);clock.advance(120);
        clock.beginCallback(true,.01,32);clock.advance(120);
        require(clock.currentBeat()==.02,"Auto callback did not apply its PPQ correction");
        clock.beginCallback(true,.011,32);clock.advance(120);
        require(clock.currentBeat()==.02,"Backward Auto correction moved a frozen clock");
        clock.advance(120);require(clock.currentBeat()==.02,"Pending Auto correction was discarded");
        clock.beginCallback(true,.012,32);clock.advance(120);
        require(clock.currentBeat()==.02,"Auto callback overwrote its pending correction");
    }
    for(unsigned action=0;action<3;++action){
        rmx::Engine recording,control;setup(recording);setup(control);recording.params.set(rmx::Param::Overdub,1);
        std::array<float,256> a{},b{},x{},y{};
        for(unsigned block=0;block<4;++block){recording.process(nullptr,nullptr,a.data(),b.data(),256);control.process(nullptr,nullptr,x.data(),y.data(),256);}
        for(auto* engine:{&recording,&control})engine->enqueue({rmx::EventType::Trigger,0,1,0,0,0});
        for(unsigned block=0;block<2;++block){recording.process(nullptr,nullptr,a.data(),b.data(),256);control.process(nullptr,nullptr,x.data(),y.data(),256);}
        if(action==0)recording.params.set(rmx::Param::Overdub,0);
        else recording.enqueue({action==1?rmx::EventType::DeletePad:rmx::EventType::ClearSequence,0});
        float peak=0;
        for(unsigned block=0;block<16;++block){
            recording.process(nullptr,nullptr,a.data(),b.data(),256);control.process(nullptr,nullptr,x.data(),y.data(),256);
            for(size_t i=0;i<256;++i){peak=std::max(peak,std::abs(x[i]));require(a[i]==x[i]&&b[i]==y[i],"Pattern deletion/recording-off cut a sounding factory drum");}
        }
        require(peak>.01f,"Pattern tail guard did not exercise audible audio");
        if(action==2){
            recording.enqueue({rmx::EventType::Trigger,1,1,0,0,0});recording.process(nullptr,nullptr,a.data(),b.data(),256);
            require(recording.meters.sequenceSteps.load()==1,"Cleared factory pattern could not record another hit");
        }
    }
    for(bool overdub:{false,true}){
        // Drum-only customization leaves the default beat map and FX settings
        // intact. User and Default must therefore share their generated clock.
        rmx::Engine user,factory;
        user.params.set(rmx::Param::UserSettings,1);
        for(auto* engine:{&user,&factory}){engine->params.set(rmx::Param::Overdub,overdub);engine->params.set(rmx::Param::XRoll,1);setup(*engine);}
        std::array<float,256> a{},b{},x{},y{};float peak=0;
        for(unsigned block=0;block<1000;++block){
            const rmx::Event hit{rmx::EventType::Trigger,0,1,17,0,0},touch{rmx::EventType::RollStart,0,1,39};
            std::array<rmx::Event,2> events{hit,touch};
            const auto count=overdub?1u:2u;
            const auto actions=block==4?std::span<const rmx::Event>(events.data(),count):std::span<const rmx::Event>{};
            user.process(nullptr,nullptr,a.data(),b.data(),256,{},actions);factory.process(nullptr,nullptr,x.data(),y.data(),256,{},actions);
            for(size_t i=0;i<256;++i){peak=std::max(peak,std::abs(x[i]));require(a[i]==x[i]&&b[i]==y[i],"Drum-only User settings changed measured roll/overdub timing");}
        }
        require(peak>.1f,"User clock guard did not exercise audible drums");
    }
    {
        rmx::Engine engine;setup(engine);engine.params.set(rmx::Param::Overdub,1);std::array<float,256> a{},b{};
        engine.process(nullptr,nullptr,a.data(),b.data(),256);engine.enqueue({rmx::EventType::Trigger,0,1,0,0,0});
        engine.process(nullptr,nullptr,a.data(),b.data(),256);engine.enqueue({rmx::EventType::MutePad,0});
        engine.process(nullptr,nullptr,a.data(),b.data(),256);engine.params.set(rmx::Param::Overdub,0);
        for(unsigned block=0;block<8;++block){engine.process(nullptr,nullptr,a.data(),b.data(),256);for(float value:a)require(value==0,"Recording-off unmuted a sounding factory drum");}
    }
    for(bool protect:{false,true}){
        rmx::Engine engine;engine.params.set(rmx::Param::XLevel,1.5f);setup(engine,protect);std::array<float,256> a{},b{};
        engine.process(nullptr,nullptr,a.data(),b.data(),256);engine.enqueue({rmx::EventType::Trigger,0,1,0,0,0});float peak=0;
        for(unsigned block=0;block<128;++block){engine.process(nullptr,nullptr,a.data(),b.data(),256);for(float v:a)peak=std::max(peak,std::abs(v));}
        require(protect?peak<=.999501f:peak>1.4f,"Device/float output policy changed original high-level drum behaviour");
    }
    require(arena.used()==0,"Factory drum buffers leaked");
    std::cout<<"PASS: factory event offsets, four drums, callback allocation guard, panic/reset and device/float output policy\n";
}catch(const std::exception& e){tracking=false;std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
