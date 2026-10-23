#pragma once
#include "CardSamples.h"
#include <algorithm>
#include <array>
#include <charconv>
#include <cmath>
#include <cstdint>
#include <span>
#include <string_view>

namespace rmx {
// ADC endpoints are unsigned 16-bit readings; end0/end1 can be reversed.
// This is physical calibration, separate from presets and User effect settings.
struct PotCalibration {
    uint16_t end0{},center{32768},end1{65535};
    bool valid() const noexcept {
        const int lo=std::min(end0,end1),hi=std::max(end0,end1);
        return hi-lo>=1024&&center-lo>=256&&hi-center>=256;
    }
};
struct ControlCalibration {
    std::array<PotCalibration,11> pots{};
    float apply(unsigned channel,float raw,bool centered) const noexcept {
        if(channel>=pots.size()||!std::isfinite(raw))return 0.f;
        const auto p=pots[channel];
        if(!p.valid())return 0.f;
        const float sample=std::clamp(raw,0.f,1.f)*65535.f;
        float x=(sample-p.end0)/(static_cast<float>(p.end1)-p.end0);
        if(centered) {
            const float middle=(static_cast<float>(p.center)-p.end0)/(static_cast<float>(p.end1)-p.end0);
            x=x<=middle?.5f*x/middle:.5f+.5f*(x-middle)/(1.f-middle);
        }
        return std::clamp(x,0.f,1.f);
    }
};
inline constexpr size_t maximumCalibrationBytes=1024;
inline CardError parseControlCalibration(std::string_view text,ControlCalibration& output) noexcept {
    if(text.empty()||text.size()>maximumCalibrationBytes)return CardError::Format;
    ControlCalibration staged;uint16_t seen=0;bool header=false;
    while(!text.empty()) {
        const auto newline=text.find('\n');
        auto line=text.substr(0,newline);
        text=newline==text.npos?std::string_view{}:text.substr(newline+1);
        std::array<std::string_view,6> words{};unsigned count=0;
        while(!line.empty()) {
            const auto start=line.find_first_not_of(" \t\r");
            if(start==line.npos)break;
            line.remove_prefix(start);const auto end=line.find_first_of(" \t\r");
            if(count==words.size())return CardError::Format;
            words[count++]=line.substr(0,end);
            line=end==line.npos?std::string_view{}:line.substr(end);
        }
        if(!count)continue;
        if(!header) {
            if(count!=2||words[0]!="RMX_CAL"||words[1]!="1")return CardError::Format;
            header=true;continue;
        }
        if(count!=5||words[0]!="pot")return CardError::Format;
        unsigned values[4]{};
        for(unsigned i=0;i<4;++i) {
            const auto word=words[i+1];const auto parsed=std::from_chars(word.data(),word.data()+word.size(),values[i]);
            if(parsed.ec!=std::errc{}||parsed.ptr!=word.data()+word.size())return CardError::Format;
        }
        if(values[0]>=staged.pots.size()||(seen&(1u<<values[0]))||values[1]>65535||values[2]>65535||values[3]>65535)return CardError::Format;
        auto& p=staged.pots[values[0]];
        p={static_cast<uint16_t>(values[1]),static_cast<uint16_t>(values[2]),static_cast<uint16_t>(values[3])};
        if(!p.valid())return CardError::Format;
        seen|=1u<<values[0];
    }
    if(!header)return CardError::Format;
    output=staged;return CardError::None;
}
inline CardError readControlCalibration(SampleFile& file,ControlCalibration& output,
                                       std::span<std::byte> scratch) noexcept {
    const auto size=file.size();
    if(!size||size>maximumCalibrationBytes)return CardError::Format;
    if(scratch.size()<size)return CardError::Memory;
    if(!file.seek(0))return CardError::Read;
    size_t done=0;
    while(done<size) {
        const auto remaining=static_cast<size_t>(size)-done;
        const auto received=file.read(scratch.subspan(done,remaining));
        if(!received||received>remaining)return CardError::Read;
        done+=received;
    }
    return parseControlCalibration({reinterpret_cast<const char*>(scratch.data()),done},output);
}

// One startup fade for both channels. It starts again only after a reboot.
class StartupEnvelope {
public:
    static constexpr unsigned sampleRate=48000,fadeFrames=2400; // 50 ms
    void process(float* left,float* right,size_t frames) noexcept {
        for(size_t i=0;i<frames;++i) {
            const float gain=position<fadeFrames?static_cast<float>(position++)/fadeFrames:1.f;
            left[i]*=gain;right[i]*=gain;
        }
    }
    bool ready()const noexcept{return position>=fadeFrames;}
private:
    unsigned position{};
};
}
