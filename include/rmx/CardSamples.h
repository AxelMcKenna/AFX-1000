#pragma once
#include "Sample.h"
#include <span>
#include <string_view>

namespace rmx {
// Project SD layout; this is separate from Pioneer's RSD/SD representation.
// Read/seek may return failure or short reads. All calls occur before audio starts.
class SampleFile {
public:
    virtual ~SampleFile()=default;
    virtual uint64_t size() const noexcept=0;
    virtual bool seek(uint32_t offset) noexcept=0;
    virtual size_t read(std::span<std::byte> bytes) noexcept=0;
};
class CardFiles {
public:
    virtual ~CardFiles()=default;
    virtual SampleFile* open(unsigned slot) noexcept=0;
    virtual bool close() noexcept=0;
};
enum class CardError : uint8_t { None,NotRequested,Manifest,Open,Read,Format,BankLimit,Memory,Allocator };
struct CardSlot { bool present{};SamplePlayback playback;bool operator==(const CardSlot&)const=default; };
struct CardManifest { std::array<CardSlot,16> slots;uint8_t banks{};bool operator==(const CardManifest&)const=default; };
struct CardReport { std::array<CardError,4> banks{};uint16_t loadedSlots{}; };
CardError parseCardManifest(std::string_view text,CardManifest& result) noexcept;
// Scratch can be a small caller-owned buffer. Hardware adapters must ensure
// that their actual DMA destinations are in DMA-accessible, aligned SRAM.
CardError readCardPcm(SampleFile&,Sample&,size_t maximumFrames,std::span<std::byte> scratch);
// Each requested bank installs atomically. Omitted slots in that bank are empty;
// a rejected or unrequested bank retains all four old slots.
// Bank/candidate vectors must share the current PMR resource; no heap fallback.
CardReport loadCardSamples(const CardManifest&,CardFiles&,SampleBank&,std::span<std::byte> scratch) noexcept;
}
