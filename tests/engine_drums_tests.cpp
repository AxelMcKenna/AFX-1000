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
        clock.stop();require(!clock.start(0,.25),"Factory roll retained its selection after release");
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
