#include "rmx/CalibratedReverbUp.h"
#include "rmx/FixedArena.h"
#include <atomic>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <memory>
#include <new>
#include <stdexcept>

namespace {
thread_local bool tracking=false;
thread_local size_t allocations=0;
void require(bool value,const char* text){if(!value)throw std::runtime_error(text);}
void* allocate(size_t size,size_t alignment){
    if(tracking)++allocations;
    void* result=nullptr;
    if(alignment<=alignof(std::max_align_t))result=std::malloc(size?size:1);
    else if(posix_memalign(&result,alignment,size?size:alignment)!=0)result=nullptr;
    if(!result)throw std::bad_alloc();return result;
}
}
void* operator new(size_t size){return allocate(size,alignof(std::max_align_t));}
void* operator new[](size_t size){return ::operator new(size);}
void* operator new(size_t size,std::align_val_t alignment){return allocate(size,static_cast<size_t>(alignment));}
void* operator new[](size_t size,std::align_val_t alignment){return ::operator new(size,alignment);}
void operator delete(void* p)noexcept{std::free(p);}
void operator delete[](void* p)noexcept{std::free(p);}
void operator delete(void* p,std::align_val_t)noexcept{std::free(p);}
void operator delete[](void* p,std::align_val_t)noexcept{std::free(p);}

int main(){try{
    constexpr size_t arenaBytes=1024*1024;
    auto memory=std::make_unique<std::byte[]>(arenaBytes);rmx::FixedArena arena(memory.get(),arenaBytes);
    auto* previous=std::pmr::set_default_resource(&arena);
    struct Restore {std::pmr::memory_resource* resource;~Restore(){std::pmr::set_default_resource(resource);}} restore{previous};
    size_t bytes=0,maximumUsed=0;uint64_t frames=0;
    {
        rmx::CalibratedReverbUp a,b;
        std::array<rmx::Stereo,4097> input{},inplace{},separate{},dryA{},dryB{};
        input.fill({.125f,-.25f});inplace.fill({.75f,-.5f});
        require(!a.process(std::span<const rmx::Stereo>(input.data(),1),std::span<rmx::Stereo>(inplace.data(),1)),"Unprepared callback accepted");
        a.prepare();b.prepare();bytes=a.storageBytes();maximumUsed=arena.used();
        require(bytes<512*1024,"Up storage exceeds the declared bound");
        require(a.process({},{}),"Empty callback rejected");
        for(const auto invalid:{size_t{0},size_t{4097}}){
            bool rejected=false;try{a.prepare(invalid);}catch(const std::invalid_argument&){rejected=true;}
            require(rejected&&a.storageBytes()==bytes,"Invalid prepare changed storage");
        }
        tracking=true;
        const auto before=arena.allocations();
        require(!a.process(input,inplace),"Oversized callback accepted");
        require(inplace[0].l==.75f,"Rejected callback wrote output");
        require(!a.process(std::span<const rmx::Stereo>(input.data(),2),std::span<rmx::Stereo>(inplace.data(),1)),"Mismatched output accepted");
        input[0].l=std::numeric_limits<float>::quiet_NaN();
        require(!a.process(std::span<const rmx::Stereo>(input.data(),1),std::span<rmx::Stereo>(inplace.data(),1)),"Non-finite callback accepted");
        input[0].l=.125f;
        require(!a.process(std::span<const rmx::Stereo>(input.data(),1),std::span<rmx::Stereo>(inplace.data(),1),std::span<rmx::Stereo>(inplace.data(),1)),"Aliased dry trace accepted");
        require(!a.process(std::span<const rmx::Stereo>(input.data(),2),std::span<rmx::Stereo>(inplace.data(),2),std::span<rmx::Stereo>(dryA.data(),1)),"Mismatched dry extent accepted");
        require(!a.process(std::span<const rmx::Stereo>(input.data(),2),std::span<rmx::Stereo>(inplace.data(),2),std::span<rmx::Stereo>(inplace.data()+1,2)),"Partially overlapping dry trace accepted");
        require(!a.process(std::span<const rmx::Stereo>(input.data(),2),std::span<rmx::Stereo>(inplace.data()+1,2),std::span<rmx::Stereo>(inplace.data(),2)),"Reverse-overlapping dry trace accepted");
        input[1].r=std::numeric_limits<float>::infinity();
        require(!a.process(std::span<const rmx::Stereo>(input.data(),2),std::span<rmx::Stereo>(inplace.data(),2)),"Later non-finite input accepted");
        require(inplace[0].l==.75f&&inplace[1].l==.75f,"Invalid callback partially wrote output");
        input[1].r=-.25f;
        uint32_t random=0xA17028;
        constexpr size_t sizes[]{1,9,15,31,32,47,128,255,4096};
        for(size_t block=0;block<512;++block){
            const auto n=sizes[block%std::size(sizes)];
            for(size_t i=0;i<n;++i){random^=random<<13;random^=random>>17;random^=random<<5;const float value=static_cast<float>(static_cast<int32_t>(random))/2147483648.f*.02f;input[i]={value,-value*.7f};inplace[i]=input[i];}
            const rmx::CalibratedReverbUp::Controls controls{static_cast<int>((block*17)%300)-20,
                static_cast<int>((block*29)%280)-10,static_cast<int>((block*43)%270),block%7!=0};
            a.setControls(controls);b.setControls(controls);
            if(block==100||block==300){a.reset();b.reset();}
            const auto incoming=std::span<const rmx::Stereo>(input.data(),n);
            const auto alias=std::span<rmx::Stereo>(inplace.data(),n);
            const auto result=std::span<rmx::Stereo>(separate.data(),n);
            const auto traceA=block%2?std::span<rmx::Stereo>(dryA.data(),n):std::span<rmx::Stereo>{};
            require(a.process(alias,alias,traceA),"In-place callback rejected");
            require(b.process(incoming,result,std::span<rmx::Stereo>(dryB.data(),n)),"Separate callback rejected");
            require(std::memcmp(inplace.data(),separate.data(),n*sizeof(rmx::Stereo))==0,"In-place output or invalid-call state differs");
            if(!traceA.empty())require(std::memcmp(dryA.data(),dryB.data(),n*sizeof(rmx::Stereo))==0,"Optional dry trace changes state");
            for(size_t i=0;i<n;++i)require(std::isfinite(inplace[i].l)&&std::isfinite(inplace[i].r),"Up callback produced non-finite audio");
            frames+=n;
        }
        require(allocations==0&&arena.allocations()==before,"Up callback/reset/control allocated memory");
        tracking=false;
        require(a.storageBytes()==bytes,"Up storage grew while processing");
    }
    require(arena.used()==0,"Up PMR storage leaked");
    std::cout<<"Up processor object: "<<sizeof(rmx::CalibratedReverbUp)<<" bytes\nUp prepared buffers (4096-frame capacity): "<<bytes
        <<" bytes\nTwo processors in bounded arena: "<<maximumUsed<<" bytes\nProcessed frames per processor: "<<frames
        <<"\nPASS: zero callback allocations, in-place parity, invalid-call atomicity, reset and bounded storage\n";
}catch(const std::exception& e){tracking=false;std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
