#include "rmx/Engine.h"
#include "rmx/FixedArena.h"
#include <iostream>
#include <memory>
#include <stdexcept>

int main() {
    constexpr size_t bytes=60u*1024*1024;
    auto storage=std::make_unique<std::byte[]>(bytes);
    rmx::FixedArena arena(storage.get(),bytes);
    auto* previous=std::pmr::set_default_resource(&arena);
    try {
        {
            rmx::Engine engine; engine.prepare(48000,64);
            const auto engineBytes=arena.used();
            auto bank=rmx::makeFactoryBank(); engine.setBank(&bank);
            const auto factoryBytes=arena.used();
            // Four banks, each with sixteen seconds total. This exercises
            // real allocations, replacement/free/coalescing, not an estimate.
            for(auto& slot:bank.slots) slot.frames.resize(48000*4);
            const auto fullBytes=arena.used();
            std::array<float,64> in{},left{},right{};
            const auto before=arena.allocations();
            engine.params.set(rmx::Param::SceneOn,1);
            for(int mode=0;mode<4;++mode) for(int scene=0;scene<10;++scene) {
                engine.params.set(rmx::Param::IsolateMode,static_cast<float>(mode));engine.params.set(rmx::Param::SceneType,static_cast<float>(scene));
                for(auto p:{rmx::Param::Low,rmx::Param::Mid,rmx::Param::High}) engine.params.set(p,mode%2?-.9f:1.f);
                for(int i=0;i<100;++i) engine.process(in.data(),in.data(),left.data(),right.data(),64);
            }
            engine.params.set(rmx::Param::SampleSource,1);
            for(unsigned bankIndex=0;bankIndex<4;++bankIndex) {
                bank.slots[bankIndex*4].playback={120,true};
                engine.params.set(rmx::Param::Bank,static_cast<float>(bankIndex));engine.enqueue({rmx::EventType::Trigger,0});
                engine.process(in.data(),in.data(),left.data(),right.data(),64);
            }
            engine.params.set(rmx::Param::XSource,1);engine.enqueue({rmx::EventType::RollStart});
            for(int i=0;i<100;++i) engine.process(in.data(),in.data(),left.data(),right.data(),64);
            if(arena.allocations()!=before) throw std::runtime_error("Embedded audio allocated SDRAM");
            std::cout<<"48 kHz engine buffers: "<<engineBytes<<" bytes\nEngine + factory bank: "<<factoryBytes<<" bytes\nEngine + 64 seconds of stereo samples: "<<fullBytes<<" bytes\nPeak during replacement: "<<arena.peak()<<" bytes\nArena capacity: "<<arena.capacity()<<" bytes\n";
        }
        if(arena.used()!=0) throw std::runtime_error("SDRAM allocations leaked");
        auto* whole=arena.allocate(arena.capacity(),alignof(std::max_align_t));
        bool exhausted=false;
        try { (void)arena.allocate(1); } catch(const std::bad_alloc&) { exhausted=true; }
        if(!exhausted) throw std::runtime_error("SDRAM heap fell back to internal memory");
        arena.deallocate(whole,arena.capacity(),alignof(std::max_align_t));
        std::pmr::set_default_resource(previous);
        std::cout<<"PASS: bounded allocation, sample replacement, coalescing, zero callback allocations\n";
    } catch(const std::exception& error) { std::pmr::set_default_resource(previous); std::cerr<<error.what()<<'\n'; return 1; }
}
