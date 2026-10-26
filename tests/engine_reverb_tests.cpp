#include "rmx/Engine.h"
#include "rmx/FixedArena.h"
#include <cstdlib>
#include <iostream>
#include <memory>
#include <new>
#include <stdexcept>

namespace {
thread_local bool tracking=false;
thread_local size_t allocations=0;
void require(bool value,const char* text){if(!value)throw std::runtime_error(text);}
void* allocate(size_t size,size_t alignment){
    if(tracking)++allocations;
    void* p=nullptr;
    if(alignment<=alignof(std::max_align_t))p=std::malloc(size?size:1);
    else if(posix_memalign(&p,alignment,size?size:alignment)!=0)p=nullptr;
    if(!p)throw std::bad_alloc();return p;
}
}
void* operator new(size_t n){return allocate(n,alignof(std::max_align_t));}
void* operator new[](size_t n){return ::operator new(n);}
void* operator new(size_t n,std::align_val_t a){return allocate(n,static_cast<size_t>(a));}
void* operator new[](size_t n,std::align_val_t a){return ::operator new(n,a);}
void operator delete(void* p)noexcept{std::free(p);}
void operator delete[](void* p)noexcept{std::free(p);}
void operator delete(void* p,std::align_val_t)noexcept{std::free(p);}
void operator delete[](void* p,std::align_val_t)noexcept{std::free(p);}

int main(){try{
    constexpr size_t capacity=60u*1024*1024;
    auto memory=std::make_unique<std::byte[]>(capacity);rmx::FixedArena arena(memory.get(),capacity);
    auto* previous=std::pmr::set_default_resource(&arena);
    struct Restore{std::pmr::memory_resource* previous;~Restore(){std::pmr::set_default_resource(previous);}}restore{previous};
    uint64_t total=0;size_t engineBytes=0;
    for(unsigned mode=0;mode<6;++mode){
        rmx::Engine engine;rmx::CalibratedReverbDown expected,bypass;
        const size_t prepared=mode==5?64:4096;
        engine.params.set(rmx::Param::AutoTempo,0);engine.params.set(rmx::Param::SceneType,9);
        engine.params.set(rmx::Param::SceneSource,mode==1?3:mode==4?2:0);
        engine.params.set(rmx::Param::Bypass,mode==2?1:0);engine.params.set(rmx::Param::WetOnly,mode==3?1:0);
        engine.prepare(48000,static_cast<uint32_t>(prepared));engineBytes=std::max(engineBytes,arena.used());
        expected.prepare(prepared);bypass.prepare(prepared);
        require(engine.latencySamples()==32,"Down button-off latency differs");
        std::array<float,4096> left{},right{},ol{},orr{};
        std::array<rmx::Stereo,4096> input{},wanted{},direct{};
        constexpr size_t sizes[]{1,9,15,31,32,47,128,255,4096};
        const auto before=arena.allocations();tracking=true;
        uint32_t random=0xE06127;
        for(size_t block=0;block<256;++block){
            const size_t n=sizes[block%std::size(sizes)];
            const int main=static_cast<int>((block*17+130)%256),amount=static_cast<int>((block*29+137)%256),cutoff=static_cast<int>((block*43+19)%256);
            const bool on=block%7!=0;
            engine.params.set(rmx::Param::SceneDepth,main/255.f);engine.params.set(rmx::Param::SceneTime,amount*7.f/255);
            engine.params.set(rmx::Param::SceneResonance,cutoff/255.f);engine.params.set(rmx::Param::SceneOn,on?1:0);
            for(size_t i=0;i<n;++i){random^=random<<13;random^=random>>17;random^=random<<5;
                const float x=static_cast<float>(static_cast<int32_t>(random))/2147483648.f*.02f;
                input[i]={x,-x*.7f};left[i]=x;right[i]=-x*.7f;}
            if(block==100){engine.reset();expected.reset();bypass.reset();}
            const bool panic=block==7;
            const std::array<rmx::Event,1> events{{{rmx::EventType::Panic,0,1,17}}};
            engine.process(left.data(),right.data(),ol.data(),orr.data(),static_cast<uint32_t>(n),{},panic?std::span<const rmx::Event>(events):std::span<const rmx::Event>{});
            for(size_t start=0;start<n;){
                size_t end=std::min(n,start+prepared);
                if(panic&&start<17&&end>17)end=17;
                const bool selected=on&&(!panic||start<17);
                expected.setControls({main,amount,cutoff,mode==1||mode==2?false:selected});bypass.setControls({main,amount,cutoff,false});
                const auto source=std::span<const rmx::Stereo>(input.data()+start,end-start);
                require(expected.process(source,std::span<rmx::Stereo>(wanted.data()+start,end-start)),"Oracle callback rejected");
                require(bypass.process(source,std::span<rmx::Stereo>(direct.data()+start,end-start)),"Bypass oracle rejected");
                start=end;
            }
            for(size_t i=0;i<n;++i){
                const auto want=mode==3?wanted[i]-direct[i]:wanted[i];
                require(ol[i]==want.l&&orr[i]==want.r,"Engine differs from the independently checked processor/routing oracle");
            }
            total+=n;
        }
        require(allocations==0&&arena.allocations()==before,"Engine callback/control/reset allocated");tracking=false;
        engine.params.set(rmx::Param::UserSettings,1);engine.params.set(rmx::Param::ReverbDownRoomSize,1);
        require(engine.latencySamples()==0,"Unsupported room profile latency differs");
        engine.params.set(rmx::Param::UserSettings,0);require(engine.latencySamples()==32,"Default profile did not mask advanced settings");
        engine.params.set(rmx::Param::SceneType,1);require(engine.latencySamples()==0,"Legacy Scene latency changed");
    }
    {
        // A real sampler voice runs on either side of FX SOURCE. Its dry bus
        // must follow the same callback timing as input, including transitions.
        rmx::SampleBank bank;auto& asset=bank.slots[0];asset.rate=48000;asset.frames.resize(16384);
        for(size_t i=0;i<asset.frames.size();++i)asset.frames[i]={.025f*std::sin(static_cast<float>(i)*.071f),.019f*std::cos(static_cast<float>(i)*.113f)};
        rmx::Engine down,dry;rmx::CalibratedReverbDown timing;
        for(auto* engine:{&down,&dry}){
            engine->setBank(&bank);engine->params.set(rmx::Param::AutoTempo,0);
            engine->params.set(rmx::Param::SampleSource,1);engine->params.set(rmx::Param::XLevel,1);
            engine->prepare(48000,128);
        }
        down.params.set(rmx::Param::SceneType,9);timing.prepare(128);timing.setControls({128,128,0,false});
        std::array<float,128> left{},right{},dl{},dr{},bl{},br{};
        std::array<rmx::Stereo,128> totalInput{},expected{};
        const auto before=arena.allocations();tracking=true;double maxError=0;
        for(unsigned block=0;block<512;++block){
            down.params.set(rmx::Param::SceneSource,static_cast<float>((block/61)%4));
            for(size_t i=0;i<left.size();++i){left[i]=.013f*std::sin(static_cast<float>(block*128+i)*.037f);right[i]=-.011f*std::cos(static_cast<float>(block*128+i)*.053f);}
            const std::array<rmx::Event,1> hit{{{rmx::EventType::Trigger,0,.7f,37,0,1}}};
            const auto events=block%71==0?std::span<const rmx::Event>(hit):std::span<const rmx::Event>{};
            if(block==300){down.reset();dry.reset();timing.reset();}
            dry.process(left.data(),right.data(),bl.data(),br.data(),128,{},events);
            down.process(left.data(),right.data(),dl.data(),dr.data(),128,{},events);
            for(size_t i=0;i<left.size();++i)totalInput[i]={bl[i],br[i]};
            require(timing.process(totalInput,expected),"Sampler timing oracle rejected callback");
            for(size_t i=0;i<left.size();++i){maxError=std::max(maxError,static_cast<double>(std::max(std::abs(dl[i]-expected[i].l),std::abs(dr[i]-expected[i].r))));}
        }
        require(maxError<1e-7,"Sampler and input dry buses acquired different callback timing");
        require(allocations==0&&arena.allocations()==before,"Sampler/source transitions allocated");tracking=false;
        std::cout<<"Sampler/input parallel-route max error: "<<maxError<<"\n";
    }
    require(arena.used()==0,"Engine routing buffers leaked");
    std::cout<<"Engine prepared PMR storage (4096 capacity): "<<engineBytes<<" bytes\nProcessed frames: "<<total
        <<"\nPASS: input/both/unselected/master bypass/wet-only routing, panic offset, reset, oversized splitting, latency and zero callback allocations\n";
}catch(const std::exception& e){tracking=false;std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
