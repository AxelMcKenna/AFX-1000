#include "CardStorage.h"
#include <cstring>

namespace rmx::board {
static_assert(offsetof(FIL,buf)%4==0&&offsetof(FATFS,win)%4==0,"SDMMC DMA requires word-aligned FatFS sector windows");
FRESULT CardStorage::Reader::openPath(const char* path) noexcept {
    if(opened&&!closeFile())return FR_DISK_ERR;
    const auto result=f_open(&file,path,FA_READ);opened=result==FR_OK;return result;
}
bool CardStorage::Reader::closeFile() noexcept {
    if(!opened)return true;
    opened=false;return f_close(&file)==FR_OK;
}
uint64_t CardStorage::Reader::size()const noexcept {return opened?f_size(&file):0;}
bool CardStorage::Reader::seek(uint32_t offset) noexcept {
    return opened&&offset<=f_size(&file)&&f_lseek(&file,offset)==FR_OK&&f_tell(&file)==offset;
}
size_t CardStorage::Reader::read(std::span<std::byte> output) noexcept {
    if(!opened||output.empty())return 0;
    // Full-sector direct transfers must start at a word-aligned address. First
    // consume up to three bytes through FatFS's own AXI sector window if needed.
    const size_t misalignment=f_tell(&file)&3u;
    const auto requested=static_cast<UINT>(std::min(output.size(),misalignment?4-misalignment:bounce.size()));
    UINT received=0;
    if(f_read(&file,bounce.data(),requested,&received)!=FR_OK)return 0;
    std::memcpy(output.data(),bounce.data(),received);return received;
}
SampleFile* CardStorage::open(unsigned slot) noexcept {
    if(slot>=16)return nullptr;
    char path[]="0:/RMX/B1S1.WAV";path[8]=static_cast<char>('1'+slot/4);path[10]=static_cast<char>('1'+slot%4);
    return reader.openPath(path)==FR_OK?&reader:nullptr;
}
CardError CardStorage::loadSettings(ParameterStore& parameters) noexcept {
    const auto opened=reader.openPath("0:/RMX/USER.TXT");
    if(opened==FR_NO_FILE||opened==FR_NO_PATH)return CardError::NotRequested;
    if(opened!=FR_OK)return CardError::Open;
    CardUserSettings user;std::array<std::byte,512> scratch{};
    auto error=readCardSettings(reader,user,scratch);
    if(!reader.closeFile())error=CardError::Read;
    if(error==CardError::None)user.apply(parameters);
    return error;
}
CardState CardStorage::load(SampleBank& bank,ParameterStore& parameters) noexcept {
    report={};report.banks.fill(CardError::NotRequested);settingsError=CardError::NotRequested;
    daisy::SdmmcHandler::Config config;config.Defaults();config.speed=daisy::SdmmcHandler::Speed::STANDARD;
    if(sdmmc.Init(config)!=daisy::SdmmcHandler::Result::OK||filesystem.Init(daisy::FatFSInterface::Config::MEDIA_SD)!=daisy::FatFSInterface::OK)return CardState::IoError;
    auto finish=[&](CardState state) {
        reader.closeFile();f_mount(nullptr,filesystem.GetSDPath(),0);filesystem.DeInit();
        const bool settingsFailed=settingsError!=CardError::None&&settingsError!=CardError::NotRequested;
        if(state==CardState::NoManifest&&settingsError==CardError::None)return CardState::Loaded;
        if((state==CardState::Loaded||state==CardState::NoManifest)&&settingsFailed)return CardState::Partial;
        if((state==CardState::ManifestError||state==CardState::IoError)&&settingsError==CardError::None)return CardState::Partial;
        return state;
    };
    const auto mount=f_mount(&filesystem.GetSDFileSystem(),filesystem.GetSDPath(),1);
    if(mount!=FR_OK)return finish(mount==FR_NOT_READY?CardState::Absent:CardState::IoError);
    // Settings and sample banks install independently; an invalid profile must
    // not overwrite physical controls or prevent valid sample banks loading.
    settingsError=loadSettings(parameters);
    const auto opened=reader.openPath("0:/RMX/SAMPLES.TXT");
    if(opened!=FR_OK)return finish(opened==FR_NO_FILE||opened==FR_NO_PATH?CardState::NoManifest:CardState::IoError);
    const auto length=reader.size();if(!length||length>2048)return finish(CardState::ManifestError);
    std::array<char,2048> text{};size_t copied=0;
    while(copied<length) {
        const auto count=reader.read({reinterpret_cast<std::byte*>(text.data()+copied),static_cast<size_t>(length)-copied});
        if(!count)return finish(CardState::IoError);
        copied+=count;
    }
    if(!reader.closeFile())return finish(CardState::IoError);
    CardManifest manifest;
    if(parseCardManifest({text.data(),copied},manifest)!=CardError::None)return finish(CardState::ManifestError);
    // Decoder scratch lives on the CPU stack, but actual SD DMA always lands
    // in Reader's aligned AXI bounce buffer or FatFS's AXI sector windows.
    std::array<std::byte,4096> scratch{};
    report=loadCardSamples(manifest,*this,bank,scratch);
    bool failed=false;for(auto error:report.banks)failed|=error!=CardError::None&&error!=CardError::NotRequested;
    return finish(failed?CardState::Partial:CardState::Loaded);
}
}
