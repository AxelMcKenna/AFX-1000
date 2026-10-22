#include "rmx/CardSamples.h"
#include "rmx/CardExport.h"
#include "rmx/CardSettings.h"
#include "rmx/Engine.h"
#include "rmx/FixedArena.h"
#include "rmx/Wav.h"
#include <chrono>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>

using namespace rmx;
void require(bool ok,const char* message) {if(!ok)throw std::runtime_error(message);}
void put16(std::vector<std::byte>& out,uint16_t n) {out.push_back(std::byte(n));out.push_back(std::byte(n>>8));}
void put32(std::vector<std::byte>& out,uint32_t n) {put16(out,static_cast<uint16_t>(n));put16(out,static_cast<uint16_t>(n>>16));}
void text(std::vector<std::byte>& out,const char* s) {for(unsigned i=0;i<4;++i)out.push_back(std::byte(s[i]));}
std::vector<std::byte> pcm(unsigned bits,unsigned channels,size_t frames,bool junk=false,bool dataFirst=false) {
    std::vector<std::byte> format;put16(format,1);put16(format,static_cast<uint16_t>(channels));put32(format,48000);
    put32(format,48000*channels*(bits/8));put16(format,static_cast<uint16_t>(channels*(bits/8)));put16(format,static_cast<uint16_t>(bits));
    std::vector<std::byte> data;data.reserve(frames*channels*(bits/8));
    for(size_t i=0;i<frames;++i)for(unsigned c=0;c<channels;++c) {
        const int32_t value=c?-static_cast<int32_t>(1u<<(bits-3)):static_cast<int32_t>(1u<<(bits-3));
        const auto encoded=static_cast<uint32_t>(value);put16(data,static_cast<uint16_t>(encoded));if(bits==24)data.push_back(std::byte(encoded>>16));
    }
    std::vector<std::byte> result;text(result,"RIFF");put32(result,0);text(result,"WAVE");
    auto chunk=[&](const char* name,const auto& bytes) {text(result,name);put32(result,static_cast<uint32_t>(bytes.size()));result.insert(result.end(),bytes.begin(),bytes.end());if(bytes.size()&1)result.push_back(std::byte{});};
    if(junk)chunk("JUNK",std::array<std::byte,3>{});
    if(dataFirst)chunk("data",data);
    chunk("fmt ",format);if(!dataFirst)chunk("data",data);
    const auto length=static_cast<uint32_t>(result.size()-8);for(unsigned i=0;i<4;++i)result[4+i]=std::byte(length>>(i*8));return result;
}
struct MemoryFile final : SampleFile {
    std::vector<std::byte> bytes;size_t position{},fragment{SIZE_MAX},failAfter{SIZE_MAX},reads{};
    uint64_t size()const noexcept override {return bytes.size();}
    bool seek(uint32_t offset)noexcept override {if(offset>bytes.size())return false;position=offset;return true;}
    size_t read(std::span<std::byte> output)noexcept override {
        ++reads;if(position>=failAfter)return 0;
        const auto n=std::min({output.size(),fragment,bytes.size()-position,failAfter-position});
        std::memcpy(output.data(),bytes.data()+position,n);position+=n;return n;
    }
};
struct MemoryFiles final : CardFiles {
    std::array<MemoryFile,16> slots;std::array<bool,16> failedClose{};int active{-1};size_t opens{},closes{};
    SampleFile* open(unsigned slot)noexcept override {++opens;if(slot>=16||slots[slot].bytes.empty())return nullptr;active=static_cast<int>(slot);slots[slot].position=0;return &slots[slot];}
    bool close()noexcept override {++closes;const bool ok=active<0||!failedClose[static_cast<size_t>(active)];active=-1;return ok;}
};
struct ArenaScope {
    std::vector<std::byte> memory;FixedArena arena;std::pmr::memory_resource* previous;
    explicit ArenaScope(size_t bytes):memory(bytes),arena(memory.data(),memory.size()),previous(std::pmr::set_default_resource(&arena)){}
    ~ArenaScope(){std::pmr::set_default_resource(previous);}
};
struct DiskFiles final : CardFiles,SampleFile {
    std::filesystem::path root;std::ifstream stream;uint64_t length{};
    explicit DiskFiles(std::filesystem::path directory):root(std::move(directory)){}
    SampleFile* open(unsigned slot)noexcept override {
        try {stream.clear();const auto path=root/("B"+std::to_string(slot/4+1)+"S"+std::to_string(slot%4+1)+".WAV");stream.open(path,std::ios::binary);if(!stream)return nullptr;length=std::filesystem::file_size(path);return this;}catch(...){return nullptr;}
    }
    bool close()noexcept override {stream.close();return !stream.fail();}
    uint64_t size()const noexcept override {return length;}
    bool seek(uint32_t offset)noexcept override {stream.clear();stream.seekg(offset);return bool(stream);}
    size_t read(std::span<std::byte> out)noexcept override {stream.read(reinterpret_cast<char*>(out.data()),static_cast<std::streamsize>(out.size()));return static_cast<size_t>(stream.gcount());}
};
int main(){try {
    {
        CardManifest manifest;require(parseCardManifest("RMX_SAMPLES 1\r\nslot 0 1 128.25\r\nslot 15 0 200\n",manifest)==CardError::None,"Card manifest rejected valid metadata");
        const auto previous=manifest;
        for(const auto& invalid:std::vector<std::string>{"", "RMX_SAMPLES 2\n", "RMX_SAMPLES 1\nslot 1 1 120\n", "RMX_SAMPLES 1\nslot 16 0 120\n", "RMX_SAMPLES 1\nslot 0 0 69\n", "RMX_SAMPLES 1\nslot 0 0 nan\n", "RMX_SAMPLES 1\nslot 0 0 120\nslot 0 0 120\n",std::string(2049,' ')}) {
            require(parseCardManifest(invalid,manifest)==CardError::Manifest&&manifest==previous,"Invalid manifest partly installed or accepted");
        }
    }
    for(unsigned bits:{16u,24u})for(unsigned channels:{1u,2u})for(bool reversed:{false,true}) {
        MemoryFile file;file.bytes=pcm(bits,channels,117,true,reversed);file.fragment=7;
        std::array<std::byte,31> scratch{};Sample sample;
        require(readCardPcm(file,sample,117,scratch)==CardError::None&&sample.frames.size()==117,"Fragmented PCM/odd chunk/format ordering decode failed");
        for(auto frame:sample.frames)require(frame.l==.25f&&frame.r==(channels==1?.25f:-.25f),"PCM signed sample decoding or channel mapping differs");
        require(readCardPcm(file,sample,116,scratch)==CardError::BankLimit,"PCM bank frame budget was not enforced");
    }
    {
        MemoryFile file;file.bytes=pcm(24,2,20);std::array<std::byte,64> scratch{};Sample sample;
        file.failAfter=50;require(readCardPcm(file,sample,100,scratch)==CardError::Read,"Partial card read was accepted");
        file.failAfter=SIZE_MAX;file.bytes[24]=std::byte{0};require(readCardPcm(file,sample,100,scratch)==CardError::Format,"Unsupported PCM rate accepted");
        file.bytes=pcm(16,2,10);file.bytes[32]=std::byte{3};require(readCardPcm(file,sample,100,scratch)==CardError::Format,"Inconsistent PCM alignment accepted");
        file.bytes=pcm(16,1,3);file.bytes.pop_back();require(readCardPcm(file,sample,100,scratch)==CardError::Format,"Truncated RIFF was accepted");
    }
    {
        SampleBank bank;for(unsigned i=0;i<16;++i)bank.slots[i].frames={{static_cast<float>(i)/32,0}};
        for(unsigned i=0;i<4;++i)bank.internal[i].frames={{.125f*static_cast<float>(i+1),-.25f}};
        MemoryFiles files;CardManifest manifest;std::array<std::byte,512> scratch{};
        for(unsigned slot:{0u,1u,4u}){manifest.slots[slot].present=true;files.slots[slot].bytes=pcm(16,2,128);}
        files.slots[1].failAfter=48;
        const auto report=loadCardSamples(manifest,files,bank,scratch);
        require(report.banks[0]==CardError::Read&&report.banks[1]==CardError::None&&report.loadedSlots==(1u<<4),"Bank load report did not isolate failure");
        require(bank.slots[0].frames.size()==1&&bank.slots[1].frames[0].l==1.f/32&&bank.slots[4].frames.size()==128,"Failed bank partly replaced its original slots");
        require(bank.slots[5].frames.empty()&&bank.slots[6].frames.empty()&&bank.slots[7].frames.empty(),"Empty card slots retained sounds from the previous bank");
        require(files.opens==files.closes,"Failed card load leaked an open file");
        files.slots[1].failAfter=SIZE_MAX;files.failedClose[0]=true;
        require(loadCardSamples(manifest,files,bank,scratch).banks[0]==CardError::Read&&bank.slots[0].frames.size()==1,"File close failure committed a bank");
        CardManifest empty;require(parseCardManifest("RMX_SAMPLES 1\nbank 0\n",empty)==CardError::None,"Explicit empty bank was rejected");
        require(loadCardSamples(empty,files,bank,scratch).banks[0]==CardError::None&&bank.slots[0].frames.empty(),"Explicit empty bank did not clear previous samples");
        for(unsigned i=0;i<4;++i)require(bank.internal[i].frames.size()==1&&bank.internal[i].frames[0].l==.125f*(i+1)&&bank.internal[i].frames[0].r==-.25f,"SD replacement changed the internal drums");
    }
    {
        ArenaScope memory(8192);SampleBank bank;bank.slots[0].frames={{.1f,.1f}};
        MemoryFiles files;files.slots[0].bytes=pcm(24,2,48000);CardManifest manifest;manifest.slots[0].present=true;std::array<std::byte,512> scratch{};
        const auto before=memory.arena.used();const auto report=loadCardSamples(manifest,files,bank,scratch);
        require(report.banks[0]==CardError::Memory&&memory.arena.used()==before&&bank.slots[0].frames.size()==1,"SDRAM exhaustion changed assets or leaked memory");
    }
    {
        SampleBank bank;bank.slots[0].frames={{.1f,.1f}};MemoryFiles files;CardManifest manifest;std::array<std::byte,4096> scratch{};
        manifest.slots[0].present=manifest.slots[1].present=true;
        files.slots[0].bytes=pcm(24,2,8*48000);files.slots[1].bytes=pcm(24,2,8*48000+1);
        require(loadCardSamples(manifest,files,bank,scratch).banks[0]==CardError::BankLimit&&bank.slots[0].frames.size()==1,"Combined SD bank overflow committed assets");
        files.slots[0].bytes.clear();
        require(loadCardSamples(manifest,files,bank,scratch).banks[0]==CardError::Open&&bank.slots[0].frames.size()==1,"Missing WAV was accepted");
        ArenaScope otherResource(8192);
        require(loadCardSamples(manifest,files,bank,scratch).banks[0]==CardError::Allocator,"SD candidate silently used a different allocator");
    }
    {
        ArenaScope memory(60u*1024*1024);Engine engine;engine.prepare(48000,64);SampleBank bank=makeFactoryBank(48000,false);
        for(auto& slot:bank.slots)slot.frames.resize(48000*4);engine.setBank(&bank);
        MemoryFiles files;CardManifest manifest;for(unsigned slot=0;slot<16;++slot){manifest.slots[slot]={true,{120,slot%4==0}};files.slots[slot].bytes=pcm(24,2,48000*4);}
        std::array<std::byte,4096> scratch{};const auto report=loadCardSamples(manifest,files,bank,scratch);
        require(report.loadedSlots==0xffff,"Full card did not fit the real bounded SDRAM arena");
        for(auto error:report.banks)require(error==CardError::None,"Full 16-second bank was rejected");
        const auto allocations=memory.arena.allocations();std::array<float,64> left{},right{};
        engine.params.set(Param::SampleSource,1);engine.enqueue({EventType::Trigger,0});for(unsigned block=0;block<100;++block)engine.process(nullptr,nullptr,left.data(),right.data(),64);
        require(memory.arena.allocations()==allocations,"Card-loaded loop allocated during audio processing");
        require(std::abs(left[32])>.1f,"Card allocation test did not play its loaded bank sample");
        std::cout<<"Full card replacement peak: "<<memory.arena.peak()<<" / "<<memory.arena.capacity()<<" bytes\n";
    }
    {
        const auto root=std::filesystem::temp_directory_path()/("rmx-card-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
        std::filesystem::create_directory(root);
        try {
            Sample source;source.frames.assign(480,{.2f,-.3f});writeWav(root/"loop.wav",source);
            State state;state.samplePaths[0]="loop.wav";state.samplePlayback[0]={128.25,true};
            state.values[static_cast<size_t>(Param::XPadBeat1)]=7;state.values[static_cast<size_t>(Param::EchoDelay1)]=8;
            state.values[static_cast<size_t>(Param::ReleaseKeepScene)]=1;
            exportCardSamples(state,root,root/"card");
            std::ifstream userIn(root/"card/RMX/USER.TXT",std::ios::binary);std::string userText((std::istreambuf_iterator<char>(userIn)),{});
            MemoryFile userFile;userFile.bytes.resize(userText.size());std::memcpy(userFile.bytes.data(),userText.data(),userText.size());userFile.fragment=5;
            CardUserSettings loadedUser;std::array<std::byte,127> settingsScratch{};
            require(readCardSettings(userFile,loadedUser,settingsScratch)==CardError::None,"Exported User settings were not readable by firmware parser");
            for(size_t i=0;i<parameterCount;++i)if(parameters[i].advanced)require(loadedUser.values[i]==state.values[i],"Card export changed stored User values");
            require(userText.find("param user_settings")==std::string::npos&&userText.find("param release_amount")==std::string::npos,"Card profile included performance/physical controls");
            auto settingsOnly=state;settingsOnly.samplePaths[0]="unavailable.wav";
            exportCardSamples(settingsOnly,root,root/"settings-only",CardExportMode::UserOnly);
            require(std::filesystem::exists(root/"settings-only/RMX/USER.TXT")&&!std::filesystem::exists(root/"settings-only/RMX/SAMPLES.TXT")&&!std::filesystem::exists(root/"settings-only/RMX/B1S1.WAV"),"Settings-only export required audio files or exported samples");
            exportCardSamples(state,root,root/"samples-only",CardExportMode::SamplesOnly);
            require(!std::filesystem::exists(root/"samples-only/RMX/USER.TXT")&&std::filesystem::exists(root/"samples-only/RMX/SAMPLES.TXT"),"Sample-only export overwrote User settings");
            auto invalidUser=state;invalidUser.values[static_cast<size_t>(Param::XPadBeat1)]=1.5f;bool invalidRejected=false;
            try{exportCardSamples(invalidUser,root,root/"invalid-user");}catch(...){invalidRejected=true;}
            require(invalidRejected&&!std::filesystem::exists(root/"invalid-user")&&!std::filesystem::exists(root/"invalid-user.rmx-staging"),"Invalid User settings left a partial card export");
            std::ifstream in(root/"card/RMX/SAMPLES.TXT",std::ios::binary);std::string content((std::istreambuf_iterator<char>(in)),{});CardManifest manifest;
            require(parseCardManifest(content,manifest)==CardError::None,"Exported manifest was not readable by firmware parser");
            SampleBank destination;DiskFiles disk(root/"card/RMX");std::array<std::byte,4096> scratch{};
            require(loadCardSamples(manifest,disk,destination,scratch).loadedSlots==0xffff,"Exported WAVs were not readable by firmware decoder");
            require(destination.slots[0].frames.size()==source.frames.size()&&destination.slots[0].playback==SamplePlayback{128.25,true},"Card export lost playback metadata or frames");
            require(std::abs(destination.slots[0].frames[100].l-.2f)<1.2e-7&&std::abs(destination.slots[0].frames[100].r+.3f)<1.2e-7,"Card PCM conversion exceeded 24-bit quantization");
            bool rejected=false;try{exportCardSamples(state,root,root/"card");}catch(...){rejected=true;}require(rejected&&std::filesystem::exists(root/"card/RMX/SAMPLES.TXT"),"Export overwrote an existing folder");
            source.frames[0].l=2;writeWav(root/"loop.wav",source);rejected=false;try{exportCardSamples(state,root,root/"failed");}catch(...){rejected=true;}
            require(rejected&&!std::filesystem::exists(root/"failed")&&!std::filesystem::exists(root/"failed.rmx-staging"),"Failed card conversion left a partial export");
        }catch(...){std::filesystem::remove_all(root);throw;}
        std::filesystem::remove_all(root);
    }
    std::cout<<"PASS: SD manifest/PCM, bank rollback, bounded replacement and exporter roundtrip\n";
}catch(const std::exception& error){std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;} }
