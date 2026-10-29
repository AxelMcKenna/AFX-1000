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
    constexpr size_t bytes=60u*1024*1024;
    auto memory=std::make_unique<std::byte[]>(bytes);rmx::FixedArena arena(memory.get(),bytes);
    auto* old=std::pmr::set_default_resource(&arena);
    struct Restore{std::pmr::memory_resource* p;~Restore(){std::pmr::set_default_resource(p);}}restore{old};
    {
        rmx::Engine engine;engine.setOutputProtection(false);
        engine.params.set(rmx::Param::AutoTempo,0);engine.params.set(rmx::Param::Quantize,0);
        engine.prepare(48000,64);
        std::array<float,509> input{},right{},left{},out{};
        std::array<rmx::Stereo,509> first{};
        const auto before=arena.allocations();tracking=true;
        for(unsigned type=0;type<3;++type){
            engine.params.set(rmx::Param::ReleaseType,static_cast<float>(type));
            for(unsigned repetition=0;repetition<2;++repetition){
                engine.params.set(rmx::Param::ReleaseAmount,0);engine.params.set(rmx::Param::UserSettings,0);engine.reset();
                for(unsigned block=0;block<480;++block){
                    if(block%71==0)engine.params.set(rmx::Param::ReleaseAmount,(block%142?255.f:110.f)/255);
                    if(block%71==69)engine.params.set(rmx::Param::ReleaseAmount,0);
                    const unsigned count=block%2?37:509;
                    for(unsigned i=0;i<count;++i){input[i]=.09f*std::sin(static_cast<float>(block*509+i)*.127f);right[i]=.06f*std::cos(static_cast<float>(block*509+i)*.079f);}
                    engine.process(input.data(),right.data(),left.data(),out.data(),count);
                    for(unsigned i=0;i<count;++i)require(std::isfinite(left[i])&&std::isfinite(out[i]),"Release produced nonfinite output");
                    if(block==479){
                        if(!repetition)for(unsigned i=0;i<count;++i)first[i]={left[i],out[i]};
                        else for(unsigned i=0;i<count;++i)require(first[i].l==left[i]&&first[i].r==out[i],"Reset retained Release history or motion state");
                    }
                }
                // Shared storage must invalidate its other interpretation when
                // switching default/custom settings. Exercise both directions.
                for(unsigned mode=0;mode<8;++mode){
                    engine.params.set(rmx::Param::UserSettings,static_cast<float>(mode%2));
                    engine.process(input.data(),right.data(),left.data(),out.data(),509);
                    for(unsigned i=0;i<509;++i)require(std::isfinite(left[i])&&std::isfinite(out[i]),"Release profile transition produced nonfinite output");
                }
            }
        }
        require(allocations==0&&arena.allocations()==before,"Release callback, reset or profile transition allocated");tracking=false;
    }
    require(arena.used()==0,"Shared Release storage leaked");
    std::cout<<"PASS: three Release types, short/oversized callbacks, repeated reset, profile storage invalidation, zero callback allocations\n";
}catch(const std::exception& e){tracking=false;std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
