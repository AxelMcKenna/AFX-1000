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
    for(bool protect:{false,true}){
        rmx::Engine engine;engine.params.set(rmx::Param::XLevel,1.5f);setup(engine,protect);std::array<float,256> a{},b{};
        engine.process(nullptr,nullptr,a.data(),b.data(),256);engine.enqueue({rmx::EventType::Trigger,0,1,0,0,0});float peak=0;
        for(unsigned block=0;block<128;++block){engine.process(nullptr,nullptr,a.data(),b.data(),256);for(float v:a)peak=std::max(peak,std::abs(v));}
        require(protect?peak<=.999501f:peak>1.4f,"Device/float output policy changed original high-level drum behaviour");
    }
    require(arena.used()==0,"Factory drum buffers leaked");
    std::cout<<"PASS: factory event offsets, four drums, callback allocation guard, panic/reset and device/float output policy\n";
}catch(const std::exception& e){tracking=false;std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
