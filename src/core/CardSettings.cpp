#include "rmx/CardSettings.h"
#include <charconv>
#include <cstring>
#include <limits>
#include <cstdio>

namespace rmx {
CardUserSettings::CardUserSettings() noexcept {
    for(size_t i=0;i<parameterCount;++i)values[i]=parameters[i].initial;
}
void CardUserSettings::apply(ParameterStore& store)const noexcept {
    for(size_t i=0;i<parameterCount;++i)if(parameters[i].advanced)store.set(static_cast<Param>(i),values[i]);
}
namespace {
bool number(std::string_view word,double& value) noexcept {
    if(word.empty()||word.size()>32)return false;
    const bool negative=word.front()=='-';
    if(negative||word.front()=='+')word.remove_prefix(1);
    if(word.empty())return false;
    int exponent=0;
    const auto exponentStart=word.find_first_of("eE");
    if(exponentStart!=word.npos) {
        auto text=word.substr(exponentStart+1);word=word.substr(0,exponentStart);
        if(text.empty()||word.empty())return false;
        const bool minus=text.front()=='-';
        if(minus||text.front()=='+')text.remove_prefix(1);
        if(text.empty())return false;
        for(char c:text) {if(c<'0'||c>'9')return false;exponent=exponent*10+c-'0';if(exponent>99)return false;}
        if(minus)exponent=-exponent;
    }
    value=0;double fraction=.1;bool dot=false,digit=false;
    for(char c:word) {
        if(c=='.'&&!dot) {dot=true;continue;}
        if(c<'0'||c>'9')return false;
        digit=true;
        if(dot) {value+=(c-'0')*fraction;fraction*=.1;}
        else value=value*10+(c-'0');
    }
    while(exponent>0) {value*=10;--exponent;}
    while(exponent<0) {value*=.1;++exponent;}
    if(negative)value=-value;
    return digit&&word.back()!='.'&&std::isfinite(value);
}
struct Parser {
    CardUserSettings next;
    std::array<bool,parameterCount> seen{};
    std::array<char,128> line{};size_t length{};bool header{};
    bool row() noexcept {
        std::string_view text{line.data(),length};length=0;
        std::array<std::string_view,3> tokens{};size_t count=0;
        while(!text.empty()) {
            const auto first=text.find_first_not_of(" \t\r");if(first==text.npos)break;
            text.remove_prefix(first);if(count==tokens.size())return false;
            const auto end=text.find_first_of(" \t\r");tokens[count++]=text.substr(0,end);
            if(end==text.npos)break;
            text.remove_prefix(end);
        }
        if(!count)return true;
        if(!header) {header=count==2&&tokens[0]=="RMX_USER"&&tokens[1]=="1";return header;}
        if(count!=3||tokens[0]!="param")return false;
        for(size_t i=0;i<parameterCount;++i)if(parameters[i].id==tokens[1]) {
            const auto& info=parameters[i];double value=0;
            if(!info.advanced||seen[i]||!number(tokens[2],value)||std::abs(value)>std::numeric_limits<float>::max()||(info.discrete&&value!=std::floor(value)))return false;
            const float parsed=static_cast<float>(value);
            if(parsed<info.min||parsed>info.max||(parsed==0&&value!=0))return false;
            seen[i]=true;next.values[i]=parsed;return true;
        }
        return false;
    }
    bool feed(std::string_view text) noexcept {
        for(char c:text) {
            if(c=='\n') {if(!row())return false;}
            else {if(length==line.size())return false;line[length++]=c;}
        }
        return true;
    }
    bool finish() noexcept {return (!length||row())&&header;}
};
}
CardError parseCardSettings(std::string_view text,CardUserSettings& result) noexcept {
    if(text.empty()||text.size()>maximumCardSettingsBytes)return CardError::Format;
    Parser parser;
    if(!parser.feed(text)||!parser.finish())return CardError::Format;
    result=parser.next;return CardError::None;
}
CardError readCardSettings(SampleFile& file,CardUserSettings& result,std::span<std::byte> scratch) noexcept {
    const auto length=file.size();
    if(!length||length>maximumCardSettingsBytes)return CardError::Format;
    if(scratch.empty())return CardError::Memory;
    if(!file.seek(0))return CardError::Read;
    Parser parser;uint64_t remaining=length;
    while(remaining) {
        const auto request=static_cast<size_t>(std::min<uint64_t>(remaining,scratch.size()));
        const auto count=file.read(scratch.first(request));
        if(!count||count>request)return CardError::Read;
        if(!parser.feed({reinterpret_cast<const char*>(scratch.data()),count}))return CardError::Format;
        remaining-=count;
    }
    if(!parser.finish())return CardError::Format;
    result=parser.next;return CardError::None;
}
CardError writeCardSettings(const CardUserSettings& settings,std::span<char> output,size_t& written) noexcept {
    written=0;
    for(size_t i=0;i<parameterCount;++i)if(parameters[i].advanced) {
        const auto& info=parameters[i];const float value=settings.values[i];
        if(!std::isfinite(value)||value<info.min||value>info.max||(info.discrete&&value!=std::floor(value)))return CardError::Format;
    }
    size_t used=0;
    auto append=[&](std::string_view text) {
        if(text.size()>output.size()-used)return false;
        std::memcpy(output.data()+used,text.data(),text.size());used+=text.size();return true;
    };
    if(!append("RMX_USER 1\n"))return CardError::Memory;
    for(size_t i=0;i<parameterCount;++i)if(parameters[i].advanced) {
        std::array<char,48> digits{};
#if defined(__APPLE__)
        // Floating to_chars requires macOS 13.3; preserve the app's macOS 12
        // deployment target. %g emits no grouping; normalize its decimal mark.
        const int count=std::snprintf(digits.data(),digits.size(),"%.*g",std::numeric_limits<float>::max_digits10,static_cast<double>(settings.values[i]));
        if(count<0||static_cast<size_t>(count)>=digits.size())return CardError::Format;
        for(int j=0;j<count;++j)if(digits[static_cast<size_t>(j)]==',')digits[static_cast<size_t>(j)]='.';
        const size_t length=static_cast<size_t>(count);
#else
        const auto converted=std::to_chars(digits.data(),digits.data()+digits.size(),settings.values[i],std::chars_format::general,std::numeric_limits<float>::max_digits10);
        if(converted.ec!=std::errc{})return CardError::Format;
        const size_t length=static_cast<size_t>(converted.ptr-digits.data());
#endif
        if(!append("param ")||!append(parameters[i].id)||!append(" ")||!append({digits.data(),length})||!append("\n"))return CardError::Memory;
    }
    if(used>maximumCardSettingsBytes)return CardError::Memory;
    written=used;return CardError::None;
}
}
