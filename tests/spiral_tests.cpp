#include "rmx/CalibratedSpiral.h"
#include "rmx/Engine.h"
#include "rmx/FixedArena.h"
#include <cstdlib>
#include <iostream>
#include <limits>
#include <memory>
#include <new>
#include <stdexcept>
#include <vector>

namespace {
thread_local bool tracking=false;
thread_local size_t allocations=0;
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
void* allocate(size_t n,size_t alignment){
    if(tracking)++allocations;void* p=nullptr;
    if(alignment<=alignof(std::max_align_t))p=std::malloc(n?n:1);
    else if(posix_memalign(&p,alignment,n?n:alignment)!=0)p=nullptr;
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
    const float nan=std::numeric_limits<float>::quiet_NaN();const rmx::Stereo poison{nan,nan};
    std::vector<rmx::Stereo> coreA(rmx::CalibratedSpiral::storageFrames,poison),coreB(coreA.size()),
        rawA(rmx::CalibratedSpiral::rawStorageFrames,poison),rawB(rawA.size());
    rmx::CalibratedSpiral a,b;
    require(a.prepare(coreA,rawA)&&b.prepare(coreB,rawB),"Spiral storage preparation failed");
    std::array<rmx::Stereo,32> input{},outA{},outB{};
    tracking=true;
    for(unsigned block=0;block<1600;++block){
        if(block%401==400){a.reset();b.reset();}
        const auto part=block%320;const bool core=part<224,raw=part<288;
        a.setStorageState(core,raw);b.setStorageState(core,raw);
        if(part==224){std::fill(coreA.begin(),coreA.end(),poison);std::fill(coreB.begin(),coreB.end(),rmx::Stereo{});}
        if(part==288){std::fill(rawA.begin(),rawA.end(),poison);std::fill(rawB.begin(),rawB.end(),rmx::Stereo{});}
        const rmx::CalibratedSpiral::Controls c{(block*17)%256,(block*31)%256,(block*43)%256,block%113<79,static_cast<int>((block/71)%2)};
        a.setControls(c);b.setControls(c);
        for(unsigned i=0;i<32;++i){const float phase=static_cast<float>(block*32+i);input[i]={.07f*std::sin(phase*.137f),.05f*std::cos(phase*.079f)};}
        a.recordRaw(input);b.recordRaw(input);a.process(input,outA);b.process(input,outB);
        for(unsigned i=0;i<32;++i){
            require(std::isfinite(outA[i].l)&&std::isfinite(outA[i].r),"Unwritten or loaned Spiral history became audible");
            require(outA[i].l==outB[i].l&&outA[i].r==outB[i].r,"Spiral output depends on invalid backing-buffer contents");
        }
    }
    // An invalid re-prepare must detach storage before any subsequent callback.
    require(!a.prepare(std::span(coreA).first(coreA.size()-1),rawA),"Undersized Spiral storage accepted");
    a.setStorageState(true,true);a.recordRaw(input);a.process(input,outA);
    for(unsigned i=0;i<32;++i)require(outA[i].l==input[i].l&&outA[i].r==input[i].r,"Unprepared Spiral path consumed invalid storage");
    require(!a.prepare(coreA,std::span(coreA).subspan(1,rawA.size())),"Overlapping Spiral rings accepted");
    require(allocations==0,"Spiral reset, controls or storage transitions allocated");tracking=false;

    constexpr size_t bytes=60u*1024*1024;
    auto memory=std::make_unique<std::byte[]>(bytes);rmx::FixedArena arena(memory.get(),bytes);
    auto* old=std::pmr::set_default_resource(&arena);
    struct Restore{std::pmr::memory_resource* p;~Restore(){std::pmr::set_default_resource(p);}}restore{old};
    size_t preparedBytes=0;
    {
        rmx::Engine engine;engine.setOutputProtection(false);engine.params.set(rmx::Param::AutoTempo,0);
        engine.params.set(rmx::Param::Quantize,0);engine.params.set(rmx::Param::SceneOn,1);engine.prepare(48000,64);
        preparedBytes=arena.used();require(preparedBytes==30100112,"Spiral introduced additional prepared audio buffers");
        std::array<float,509> left{},right{},l{},r{};const auto before=arena.allocations();tracking=true;
        constexpr unsigned types[]{3,8,1,4,9,2,0,5,6,7};
        for(unsigned block=0;block<500;++block){
            engine.params.set(rmx::Param::SceneType,types[(block/5)%10]);
            engine.params.set(rmx::Param::UserSettings,block%23==0?1.f:0.f);
            engine.params.set(rmx::Param::Tempo,block%29==0?137.f:120.f);
            engine.params.set(rmx::Param::SceneSource,block%31==0?1.f:0.f);
            engine.params.set(rmx::Param::SceneOn,block%17?1.f:0.f);
            engine.params.set(rmx::Param::SceneDepth,(block*17%256)/255.f);
            engine.params.set(rmx::Param::SceneTime,(block*37%256)*(7.f/255));
            engine.params.set(rmx::Param::SceneResonance,(block*43%256)/255.f);
            const unsigned n=block%2?17:509;
            for(unsigned i=0;i<n;++i){const auto phase=static_cast<float>(block*509+i);left[i]=.05f*std::sin(phase*.137f);right[i]=.07f*std::cos(phase*.079f);}
            engine.process(left.data(),right.data(),l.data(),r.data(),n);
            for(unsigned i=0;i<n;++i)require(std::isfinite(l[i])&&std::isfinite(r[i]),"Scene storage ownership transition produced nonfinite output");
            if(block%101==100)engine.reset();
        }
        require(allocations==0&&arena.allocations()==before,"Live Spiral callback or ownership transition allocated");tracking=false;
    }
    require(arena.used()==0,"Scene backing storage leaked");
    require(sizeof(rmx::Engine)<=65536,"Engine object exceeds internal-memory budget");
    std::cout<<"Spiral object: "<<sizeof(rmx::CalibratedSpiral)<<" bytes\nEngine object: "<<sizeof(rmx::Engine)
        <<" bytes\nPrepared engine buffers: "<<preparedBytes<<" bytes\nPASS: poisoned history, aliased/undersized rings, owner withdrawal, reset, finite fallback transitions and zero callback allocations\n";
}catch(const std::exception& e){tracking=false;std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
