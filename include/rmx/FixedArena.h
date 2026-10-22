#pragma once
#include <cstddef>
#include <cstdint>
#include <memory_resource>
#include <new>
#include <algorithm>

namespace rmx {
// A bounded, coalescing SDRAM heap. Allocate/free only while audio is stopped
// (or on an adapter's dedicated asset thread). Audio processing never calls it.
// No fallback to the MCU's small internal heap. Alignment up to max_align_t.
class FixedArena final : public std::pmr::memory_resource {
public:
    FixedArena(void* memory,size_t bytes) noexcept {
        const auto address=reinterpret_cast<uintptr_t>(memory);
        const auto aligned=(address+alignment-1)&~(alignment-1);
        const auto padding=aligned-address;
        if(bytes>padding+sizeof(Block)) {
            first=new(reinterpret_cast<void*>(aligned)) Block{(bytes-padding-sizeof(Block))&~(alignment-1),nullptr,true};
            capacity_=first->size;
        }
    }
    size_t capacity() const noexcept { return capacity_; }
    size_t used() const noexcept { return used_; }
    size_t peak() const noexcept { return peak_; }
    size_t allocations() const noexcept { return allocations_; }
private:
    static constexpr size_t alignment=alignof(std::max_align_t);
    struct alignas(std::max_align_t) Block { size_t size; Block* next; bool free; };
    Block* first{}; size_t capacity_{},used_{},peak_{},allocations_{};
    void* do_allocate(size_t bytes,size_t align) override {
        if(align>alignment||bytes>capacity_) throw std::bad_alloc();
        const size_t needed=(std::max(size_t{1},bytes)+alignment-1)&~(alignment-1);
        for(auto* block=first;block;block=block->next) if(block->free&&block->size>=needed) {
            if(block->size>=needed+sizeof(Block)+alignment) {
                auto* next=new(reinterpret_cast<std::byte*>(block+1)+needed) Block{block->size-needed-sizeof(Block),block->next,true};
                block->size=needed; block->next=next;
            }
            block->free=false; used_+=block->size; peak_=std::max(peak_,used_); ++allocations_;
            return block+1;
        }
        throw std::bad_alloc();
    }
    void do_deallocate(void* pointer,size_t,size_t) override {
        if(!pointer) return;
        auto* block=static_cast<Block*>(pointer)-1;
        used_-=block->size; block->free=true;
        for(auto* current=first;current&&current->next;) {
            if(current->free&&current->next->free) { current->size+=sizeof(Block)+current->next->size; current->next=current->next->next; }
            else current=current->next;
        }
    }
    bool do_is_equal(const std::pmr::memory_resource& other) const noexcept override { return this==&other; }
};
}
