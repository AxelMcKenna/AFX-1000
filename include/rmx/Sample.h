#pragma once
#include "Dsp.h"
#include <array>
#include <limits>

namespace rmx {
struct SamplePlayback {
    // Original loop tempo. Engine tempo changes loop duration independently of
    // XPitch; one-shots retain conventional pitch-and-speed sample playback.
    double bpm{120};
    bool loop{};
    bool operator==(const SamplePlayback&) const=default;
};
inline bool validSamplePlayback(size_t slot,SamplePlayback playback) noexcept {
    return slot<16&&std::isfinite(playback.bpm)&&playback.bpm>=70&&playback.bpm<=200&&(!playback.loop||slot%4==0);
}
struct Sample { std::pmr::vector<Stereo> frames; double rate{48000};SamplePlayback playback; };
struct SampleBank { std::array<Sample,16> slots;std::array<Sample,4> internal; };
inline double sampleDuration(const Sample& sample) noexcept {
    if(!std::isfinite(sample.rate)||sample.rate<8000||sample.rate>192000)return std::numeric_limits<double>::infinity();
    return sample.frames.size()/sample.rate;
}
inline double bankDuration(const SampleBank& bank,size_t index) noexcept {
    if(index>=4)return std::numeric_limits<double>::infinity();
    double seconds=0;for(size_t pad=0;pad<4;++pad)seconds+=sampleDuration(bank.slots[index*4+pad]);return seconds;
}
// Shared storage limit for desktop imports and card preparation. Replacing a slot must fit in the original
// sixteen-second total for that bank; rates are converted by the audio adapter.
inline bool sampleFitsBank(const SampleBank& bank,size_t slot,const Sample& replacement) noexcept {
    if(slot>=16||!validSamplePlayback(slot,replacement.playback))return false;
    double seconds=sampleDuration(replacement);
    for(size_t pad=0;pad<4;++pad)if(slot/4*4+pad!=slot)seconds+=sampleDuration(bank.slots[slot/4*4+pad]);
    return std::isfinite(seconds)&&seconds<=16+1e-9;
}
}
