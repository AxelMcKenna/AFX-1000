#include "rmx/CardSettings.h"
#include "rmx/Engine.h"
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <new>
#include <stdexcept>
#include <string>
#include <vector>

static bool track{};static size_t allocations{};
void* operator new(size_t n) {if(track)++allocations;if(auto* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void* operator new[](size_t n) {return ::operator new(n);}
void operator delete(void* p)noexcept {std::free(p);}
void operator delete[](void* p)noexcept {std::free(p);}
void operator delete(void* p,size_t)noexcept {std::free(p);}
void operator delete[](void* p,size_t)noexcept {std::free(p);}
using namespace rmx;
void require(bool ok,const char* message) {if(!ok)throw std::runtime_error(message);}
struct File final : SampleFile {
    std::string text;size_t position{},fragment{SIZE_MAX},failAfter{SIZE_MAX};uint64_t advertised{};bool failedSeek{},overread{};
    uint64_t size()const noexcept override {return advertised?advertised:text.size();}
    bool seek(uint32_t offset)noexcept override {if(failedSeek||offset>text.size())return false;position=offset;return true;}
    size_t read(std::span<std::byte> out)noexcept override {
        if(overread)return out.size()+1;
        if(position>=failAfter||position>=text.size())return 0;
        const auto n=std::min({out.size(),fragment,text.size()-position,failAfter-position});
        std::memcpy(out.data(),text.data()+position,n);position+=n;return n;
    }
};
int main(){try {
    std::array<char,maximumCardSettingsBytes> output{};std::array<std::byte,31> scratch{};size_t length=0;
    {
        CardUserSettings source,copy;
        source.values[static_cast<size_t>(Param::Feedback)]=std::numeric_limits<float>::denorm_min();
        source.values[static_cast<size_t>(Param::ReverbDecay)]=.1f;
        source.values[static_cast<size_t>(Param::XPadBeat1)]=7;
        track=true;
        const auto written=writeCardSettings(source,output,length);
        const auto parsed=parseCardSettings({output.data(),length},copy);
        ParameterStore store;copy.apply(store);
        track=false;
        require(written==CardError::None&&parsed==CardError::None&&source==copy,"User card values lost precision or failed at minimum bounds");
        require(allocations==0,"User profile parsing/writing/apply allocated memory");
    }
    for(unsigned variant=0;variant<32;++variant) {
        CardUserSettings source,copy;
        for(size_t i=0;i<parameterCount;++i)if(parameters[i].advanced) {
            const auto& info=parameters[i];
            source.values[i]=sanitize(static_cast<Param>(i),info.min+(info.max-info.min)*(variant/31.f));
        }
        require(writeCardSettings(source,output,length)==CardError::None,"User export rejected a valid parameter extreme");
        File file;file.text.assign(output.data(),length);file.fragment=variant%7+1;
        track=true;const auto parsed=readCardSettings(file,copy,scratch);track=false;
        require(parsed==CardError::None&&source==copy,"Fragmented settings file lost User values");
        require(allocations==0,"Streaming User settings parser allocated");
    }
    {
        CardUserSettings user;user.values[static_cast<size_t>(Param::XPadBeat1)]=15;const auto previous=user;
        for(const auto& invalid:std::vector<std::string>{"", "RMX_USER 2\n", "RMX_USER 1\nparam unknown 1\n", "RMX_USER 1\nparam feedback nan\n", "RMX_USER 1\nparam feedback inf\n", "RMX_USER 1\nparam feedback 1e100\n", "RMX_USER 1\nparam feedback 1e-99\n", "RMX_USER 1\nparam feedback -0.1\n", "RMX_USER 1\nparam feedback 1\n", "RMX_USER 1\nparam x_pad_beat_1 1.5\n", "RMX_USER 1\nparam x_pad_beat_1 16\n", "RMX_USER 1\nparam feedback 0.5 extra\n", "RMX_USER 1\nparam feedback 0.5\nparam feedback 0.6\n", "RMX_USER 1\nparam release_amount 1\n", "RMX_USER 1\nparam user_settings 1\n", "RMX_USER 1\nparam bank 2\n", "RMX_USER 1\nparam x_level 1\n", "RMX_USER 1\nparam feedback 0.4\nparam release_amount 1\n",std::string(129,'x'),std::string(maximumCardSettingsBytes+1,' ')}) {
            require(parseCardSettings(invalid,user)==CardError::Format&&user==previous,"Invalid User profile partly installed or accepted");
        }
        require(parseCardSettings("\r\n RMX_USER 1\r\nparam feedback +5e-1\r\nparam x_pad_beat_1 7",user)==CardError::None,"Valid CRLF/scientific/final-line profile rejected");
        require(user.values[static_cast<size_t>(Param::Feedback)]==.5f&&user.values[static_cast<size_t>(Param::XPadBeat1)]==7,"Sparse User profile parsed incorrectly");
        require(user.values[static_cast<size_t>(Param::EchoDelay1)]==parameters[static_cast<size_t>(Param::EchoDelay1)].initial,"Omitted User values did not use defaults");
    }
    {
        CardUserSettings user;user.values[static_cast<size_t>(Param::XPadBeat1)]=15;const auto previous=user;
        File file;file.text="RMX_USER 1\nparam feedback 0.3\nparam x_pad_beat_1 7\n";file.fragment=3;file.failAfter=30;
        require(readCardSettings(file,user,scratch)==CardError::Read&&user==previous,"Read failure partly installed User settings");
        file.failAfter=SIZE_MAX;file.advertised=file.text.size()+1;
        require(readCardSettings(file,user,scratch)==CardError::Read&&user==previous,"Truncated profile was accepted");
        file.advertised=maximumCardSettingsBytes+1;
        require(readCardSettings(file,user,scratch)==CardError::Format&&user==previous,"Oversize profile was accepted");
        file.advertised=0;file.failedSeek=true;
        require(readCardSettings(file,user,scratch)==CardError::Read&&user==previous,"Failed profile seek was accepted");
        file.failedSeek=false;file.overread=true;
        require(readCardSettings(file,user,scratch)==CardError::Read&&user==previous,"Invalid adapter read count was accepted");
        file.overread=false;
        require(readCardSettings(file,user,{})==CardError::Memory&&user==previous,"Empty scratch buffer was accepted");
        size_t written=99;
        require(writeCardSettings(user,std::span(output).first(4),written)==CardError::Memory&&written==0,"Short export buffer reported complete data");
        user.values[static_cast<size_t>(Param::Feedback)]=std::numeric_limits<float>::quiet_NaN();
        require(writeCardSettings(user,output,written)==CardError::Format&&written==0,"Exporter accepted nonfinite User settings");
    }
    {
        Engine engine;SampleBank bank;bank.internal[0].rate=8000;bank.internal[0].frames={{.25f,-.25f}};engine.setBank(&bank);
        engine.params.set(Param::XLevel,1);engine.params.set(Param::XRoll,0);engine.params.set(Param::Quantize,0);
        engine.params.set(Param::ReleaseAmount,.4f);engine.params.set(Param::Bank,2);
        CardUserSettings user;require(parseCardSettings("RMX_USER 1\nparam x_pad_beat_1 7\n",user)==CardError::None,"Signal profile did not parse");
        user.values[static_cast<size_t>(Param::ReleaseAmount)]=1;user.values[static_cast<size_t>(Param::Bank)]=3;user.apply(engine.params);
        require(engine.params.get(Param::UserSettings)==0&&engine.params.get(Param::ReleaseAmount)==.4f&&engine.params.get(Param::Bank)==2,"User profile changed physical/performance controls");
        engine.params.set(Param::ReleaseAmount,0);
        auto hits=[&](bool custom) {
            engine.params.set(Param::UserSettings,custom?1.f:0.f);engine.prepare(8000,64);engine.enqueue({EventType::RollStart,0});
            std::array<float,64> l{},r{};std::vector<unsigned> result;
            for(unsigned offset=0;offset<3000;offset+=64) {
                const auto n=std::min(64u,3000-offset);engine.process(nullptr,nullptr,l.data(),r.data(),n);
                for(unsigned i=0;i<n;++i)if(std::abs(l[i])>.1f)result.push_back(offset+i);
            }
            return result;
        };
        require(hits(false).size()==12,"Stored User profile changed Default DSP timing");
        require(hits(true)==std::vector<unsigned>{0,1334,2668},"Card User setting did not reach audible X-Pad timing");
    }
    std::cout<<"PASS: bounded User profiles, exact float recall, no allocations, malformed/read rollback, control preservation and User/Default audio\n";
}catch(const std::exception& error){std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;} }
