#include "rmx/CardSamples.h"
#include <cstring>
#include <new>

namespace rmx {
namespace {
uint16_t u16(const std::byte* p) {return uint16_t(std::to_integer<unsigned>(p[0])|(std::to_integer<unsigned>(p[1])<<8));}
uint32_t u32(const std::byte* p) {return uint32_t(u16(p))|(uint32_t(u16(p+2))<<16);}
bool tag(const std::byte* p,const char* name) {return std::memcmp(p,name,4)==0;}
bool exact(SampleFile& file,std::span<std::byte> bytes) {
    while(!bytes.empty()) {const auto got=file.read(bytes);if(!got||got>bytes.size())return false;bytes=bytes.subspan(got);}return true;
}
bool decimal(std::string_view word,double& value) {
    if(word.empty()||word.size()>10)return false;
    value=0;double divisor=1;bool dot=false,any=false;
    for(char c:word) {
        if(c=='.'&&!dot&&any) {dot=true;continue;}
        if(c<'0'||c>'9')return false;
        any=true;if(dot) {divisor*=10;value+=(c-'0')/divisor;}else value=value*10+(c-'0');
    }
    return any&&word.back()!='.';
}
size_t words(std::string_view line,std::array<std::string_view,4>& result) {
    size_t count=0;
    while(!line.empty()) {
        const auto begin=line.find_first_not_of(" \t\r");if(begin==line.npos)break;line.remove_prefix(begin);
        const auto end=line.find_first_of(" \t\r");if(count==result.size())return count+1;
        result[count++]=line.substr(0,end);if(end==line.npos)break;line.remove_prefix(end);
    }
    return count;
}
}
CardError parseCardManifest(std::string_view text,CardManifest& result) noexcept {
    if(text.empty()||text.size()>2048)return CardError::Manifest;
    CardManifest next{};bool header=false;unsigned declaredBanks=0;
    while(!text.empty()) {
        const auto end=text.find('\n');const auto line=text.substr(0,end);
        if(end==text.npos)text={};else text.remove_prefix(end+1);
        std::array<std::string_view,4> tokens{};const auto count=words(line,tokens);if(!count)continue;
        if(!header) {if(count!=2||tokens[0]!="RMX_SAMPLES"||tokens[1]!="1")return CardError::Manifest;header=true;continue;}
        double slotNumber=0,bpm=0;
        if(count==2&&tokens[0]=="bank") {
            if(!decimal(tokens[1],slotNumber)||slotNumber>3||slotNumber!=std::floor(slotNumber))return CardError::Manifest;
            const auto bit=1u<<static_cast<unsigned>(slotNumber);if(declaredBanks&bit)return CardError::Manifest;
            declaredBanks|=bit;next.banks|=static_cast<uint8_t>(bit);continue;
        }
        if(count!=4||tokens[0]!="slot"||!decimal(tokens[1],slotNumber)||slotNumber>15||slotNumber!=std::floor(slotNumber)
            ||(tokens[2]!="0"&&tokens[2]!="1")||!decimal(tokens[3],bpm))return CardError::Manifest;
        const auto slot=static_cast<size_t>(slotNumber);const SamplePlayback playback{bpm,tokens[2]=="1"};
        if(next.slots[slot].present||!validSamplePlayback(slot,playback))return CardError::Manifest;
        next.slots[slot]={true,playback};
        next.banks|=static_cast<uint8_t>(1u<<(slot/4));
    }
    if(!header)return CardError::Manifest;
    result=next;return CardError::None;
}
CardError readCardPcm(SampleFile& file,Sample& sample,size_t maximumFrames,std::span<std::byte> scratch) {
    constexpr uint64_t maximumFileBytes=16*48000*6+65536;
    if(file.size()<44||file.size()>maximumFileBytes||!file.seek(0))return CardError::Format;
    std::array<std::byte,16> header{};if(!exact(file,std::span(header).first(12)))return CardError::Read;
    if(!tag(header.data(),"RIFF")||!tag(header.data()+8,"WAVE"))return CardError::Format;
    const uint64_t end=uint64_t(u32(header.data()+4))+8;if(end>file.size()||end<44)return CardError::Format;
    uint64_t offset=12;uint32_t dataOffset=0,dataBytes=0;uint16_t channels=0,bits=0,alignment=0;bool format=false;
    for(unsigned chunk=0;offset+8<=end&&chunk<128;++chunk) {
        if(!file.seek(static_cast<uint32_t>(offset))||!exact(file,std::span(header).first(8)))return CardError::Read;
        const uint32_t bytes=u32(header.data()+4);const uint64_t next=offset+8+bytes+(bytes&1u);
        if(next>end)return CardError::Format;
        if(tag(header.data(),"fmt ")) {
            if(format||bytes<16)return CardError::Format;
            if(!exact(file,header))return CardError::Read;
            channels=u16(header.data()+2);bits=u16(header.data()+14);alignment=u16(header.data()+12);
            if(u16(header.data())!=1||(channels!=1&&channels!=2)||(bits!=16&&bits!=24)||u32(header.data()+4)!=48000
                ||alignment!=channels*(bits/8)||u32(header.data()+8)!=48000u*alignment)return CardError::Format;
            format=true;
        } else if(tag(header.data(),"data")) {
            if(dataOffset)return CardError::Format;
            dataOffset=static_cast<uint32_t>(offset+8);dataBytes=bytes;
        }
        offset=next;
    }
    if(offset!=end||!format||!dataOffset||!dataBytes||dataBytes%alignment)return CardError::Format;
    const size_t frames=dataBytes/alignment;if(frames>maximumFrames)return CardError::BankLimit;
    if(scratch.size()<alignment)return CardError::Memory;
    sample.rate=48000;sample.frames.resize(frames);if(!file.seek(dataOffset))return CardError::Read;
    auto decode=[bits](const std::byte* p) {
        if(bits==16) {const uint32_t value=u16(p);const int32_t signedValue=value&0x8000u?static_cast<int32_t>(value)-65536:static_cast<int32_t>(value);return signedValue/32768.f;}
        const uint32_t value=u16(p)|(std::to_integer<uint32_t>(p[2])<<16);
        const int32_t signedValue=value&0x800000u?static_cast<int32_t>(value)-16777216:static_cast<int32_t>(value);return signedValue/8388608.f;
    };
    for(size_t position=0;position<frames;) {
        const size_t count=std::min(frames-position,scratch.size()/alignment);
        if(!exact(file,scratch.first(count*alignment)))return CardError::Read;
        for(size_t i=0;i<count;++i) {const auto* p=scratch.data()+i*alignment;const float left=decode(p),right=channels==2?decode(p+bits/8):left;sample.frames[position+i]={left,right};}
        position+=count;
    }
    return CardError::None;
}
CardReport loadCardSamples(const CardManifest& manifest,CardFiles& files,SampleBank& bank,std::span<std::byte> scratch) noexcept {
    CardReport report;
    for(unsigned index=0;index<4;++index) {
        auto& error=report.banks[index];error=CardError::NotRequested;bool requested=(manifest.banks&(1u<<index))!=0;
        for(unsigned pad=0;pad<4;++pad)requested|=manifest.slots[index*4+pad].present;
        if(!requested)continue;
        error=CardError::None;
        try {
            double seconds=0;
            for(unsigned pad=0;pad<4;++pad) {
                const unsigned slot=index*4+pad;
                if(bank.slots[slot].frames.get_allocator().resource()!=std::pmr::get_default_resource())error=CardError::Allocator;
                if(!validSamplePlayback(slot,manifest.slots[slot].playback))error=CardError::Manifest;
            }
            if(error!=CardError::None)continue;
            if(!std::isfinite(seconds)||seconds>16) {error=CardError::BankLimit;continue;}
            SampleBank candidate;
            for(unsigned pad=0;pad<4&&error==CardError::None;++pad) {
                const unsigned slot=index*4+pad;
                if(!manifest.slots[slot].present)continue;
                auto* file=files.open(slot);if(!file) {error=CardError::Open;break;}
                try {error=readCardPcm(*file,candidate.slots[slot],static_cast<size_t>(std::floor((16-seconds)*48000+1e-6)),scratch);}
                catch(...) {files.close();throw;}
                if(!files.close()&&error==CardError::None)error=CardError::Read;
                candidate.slots[slot].playback=manifest.slots[slot].playback;seconds+=sampleDuration(candidate.slots[slot]);
            }
            if(error==CardError::None) {
                for(unsigned pad=0;pad<4;++pad)bank.slots[index*4+pad]=std::move(candidate.slots[index*4+pad]);
                for(unsigned pad=0;pad<4;++pad)if(manifest.slots[index*4+pad].present)report.loadedSlots|=uint16_t(1u<<(index*4+pad));
            }
        } catch(const std::bad_alloc&) {error=CardError::Memory;}
        catch(...) {error=CardError::Read;}
    }
    return report;
}
}
