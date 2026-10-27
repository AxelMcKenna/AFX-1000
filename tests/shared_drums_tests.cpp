#include "rmx/Engine.h"
#include "../research/audio/experiments/SharedDrumFX.h"
#include <cstdlib>
#include <iostream>
#include <new>

namespace {
thread_local bool tracking=false;thread_local size_t allocations=0;
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
void* allocate(size_t n,size_t alignment){if(tracking)++allocations;void* p=nullptr;if(alignment<=alignof(std::max_align_t))p=std::malloc(n?n:1);else if(posix_memalign(&p,alignment,n?n:alignment)!=0)p=nullptr;if(!p)throw std::bad_alloc();return p;}
}
void* operator new(size_t n){return allocate(n,alignof(std::max_align_t));}void* operator new[](size_t n){return ::operator new(n);}
void* operator new(size_t n,std::align_val_t a){return allocate(n,static_cast<size_t>(a));}
void operator delete(void* p)noexcept{std::free(p);}void operator delete[](void* p)noexcept{std::free(p);}void operator delete(void* p,std::align_val_t)noexcept{std::free(p);}

int main(){try{
    constexpr size_t sizes[]{1,7,15,31,32,47,128,257,1023,4096};
    {
        rmx::Engine engine;engine.setOutputProtection(false);engine.params.set(rmx::Param::AutoTempo,0);engine.params.set(rmx::Param::Quantize,0);
        engine.params.set(rmx::Param::SceneType,1);engine.params.set(rmx::Param::XLevel,128*1.5f/255);engine.prepare(48000,4096);
        SharedDrumFX shared(1,0,128,64,0,false,128,128);std::array<float,4096> a{},b{};std::array<rmx::Stereo,4096> input{},output{};
        tracking=true;
        for(unsigned callback=0;callback<400;++callback){
            const unsigned pad=callback%4;shared.trigger(pad);require(engine.enqueue({rmx::EventType::Trigger,static_cast<uint8_t>(pad),1,0,0,0}),"Engine event queue full");
            const auto n=sizes[callback%std::size(sizes)];shared.process(std::span<const rmx::Stereo>(input.data(),n),std::span<rmx::Stereo>(output.data(),n));
            engine.process(nullptr,nullptr,a.data(),b.data(),static_cast<uint32_t>(n));
            for(size_t i=0;i<n;++i)require(output[i].l==a[i]&&output[i].r==b[i],"Shared drum clock differs from previously validated dry Engine");
        }
        require(allocations==0,"Shared drum callback allocated");tracking=false;
    }
    const auto reverb=[&]<class Processor>(int type){
        SharedDrumFX shared(type,0,173,91,217,true,128,128);Processor expected;expected.prepare(4096);expected.setControls({173,91,217,true});
        std::array<rmx::Stereo,4096> input{},a{},b{};uint32_t random=0x1845cf93;
        tracking=true;
        for(unsigned callback=0;callback<400;++callback){
            const auto n=sizes[callback%std::size(sizes)];for(size_t i=0;i<n;++i){random^=random<<13;random^=random>>17;random^=random<<5;const float x=static_cast<float>(static_cast<int32_t>(random))/2147483648.f*.015f;input[i]={x,-x*.7f};}
            const auto source=std::span<const rmx::Stereo>(input.data(),n);shared.process(source,std::span<rmx::Stereo>(a.data(),n));
            require(expected.process(source,std::span<rmx::Stereo>(b.data(),n)),"Reverb oracle rejected callback");
            for(size_t i=0;i<n;++i)require(a[i].l==b[i].l&&a[i].r==b[i].r,"Shared source-free reverb clock differs from validated streaming oracle");
        }
        require(allocations==0,"Shared reverb callback allocated");tracking=false;
    };
    reverb.template operator()<rmx::CalibratedReverbUp>(4);reverb.template operator()<rmx::CalibratedReverbDown>(9);
    for(const int type:{0,1,4,5,6,7,9}){
        SharedDrumFX active(type,2,137,93,type==1||type==4||type==9?109:0,true,199,177);
        std::array<rmx::Stereo,4096> input{},output{};uint32_t random=0x3258e3;double energy=0;tracking=true;
        for(unsigned block=0;block<160;++block){
            const auto n=sizes[block%std::size(sizes)];if(block%8==1)for(unsigned pad=0;pad<4;++pad)active.trigger(pad);
            for(size_t i=0;i<n;++i){random^=random<<13;random^=random>>17;random^=random<<5;const float x=static_cast<float>(static_cast<int32_t>(random))/2147483648.f*.015f;input[i]={x,-x*.7f};}
            active.process(std::span<const rmx::Stereo>(input.data(),n),std::span<rmx::Stereo>(output.data(),n));
            for(size_t i=0;i<n;++i){require(std::isfinite(output[i].l)&&std::isfinite(output[i].r),"Active shared FX produced non-finite audio");energy+=std::abs(output[i].l)+std::abs(output[i].r);}
        }
        require(allocations==0&&energy>1,"Active shared FX allocated or produced no signal");tracking=false;
    }
    std::cout<<"PASS: four dry drums, cold Up/Down input, seven active shared FX, irregular callbacks and zero callback allocations\n";
}catch(const std::exception& e){tracking=false;std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
