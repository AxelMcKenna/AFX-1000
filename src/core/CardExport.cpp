#include "rmx/CardExport.h"
#include "rmx/CardSettings.h"
#include "rmx/Engine.h"
#include "rmx/Wav.h"
#include <fstream>
#include <iomanip>
#include <optional>
#include <stdexcept>

namespace rmx {
void exportCardSamples(const State& state,const std::filesystem::path& presetDirectory,const std::filesystem::path& destination,CardExportMode mode) {
    if(mode!=CardExportMode::All&&mode!=CardExportMode::UserOnly&&mode!=CardExportMode::SamplesOnly)throw std::runtime_error("Invalid card export mode");
    if(destination.empty()||std::filesystem::exists(std::filesystem::symlink_status(destination)))throw std::runtime_error("Choose a new, unused card export directory");
    std::optional<SampleBank> bank;
    if(mode!=CardExportMode::UserOnly) {
        bank.emplace(makeFactoryBank());
        for(size_t slot=0;slot<16;++slot)if(!state.samplePaths[slot].empty()) {
            const std::filesystem::path source=state.samplePaths[slot];bank->slots[slot]=readWav(source.is_absolute()?source:presetDirectory/source);
        }
        state.applySamples(*bank);
    }
    auto staging=destination;staging+=".rmx-staging";
    if(std::filesystem::exists(staging))throw std::runtime_error("Card staging directory already exists");
    bool created=false;
    try {
        // create_directory must succeed, rather than reuse another writer's stage.
        if(!std::filesystem::create_directory(staging))throw std::runtime_error("Cannot create card staging directory");
        created=true;
        const auto directory=staging/"RMX";std::filesystem::create_directory(directory);
        if(mode!=CardExportMode::SamplesOnly) {
            CardUserSettings user;user.values=state.values;
            std::array<char,maximumCardSettingsBytes> settingsText{};size_t settingsLength=0;
            if(writeCardSettings(user,settingsText,settingsLength)!=CardError::None)throw std::runtime_error("Invalid card User settings");
            std::ofstream settings(directory/"USER.TXT",std::ios::binary);
            if(!settings)throw std::runtime_error("Cannot create card User settings");
            settings.write(settingsText.data(),static_cast<std::streamsize>(settingsLength));settings.close();
            if(!settings)throw std::runtime_error("Card User settings write failed");
        }
        if(bank) {
            std::ofstream manifest(directory/"SAMPLES.TXT",std::ios::binary);
            if(!manifest)throw std::runtime_error("Cannot create card manifest");
            manifest<<"RMX_SAMPLES 1\n"<<std::setprecision(6)<<std::fixed;
            for(unsigned bankIndex=0;bankIndex<4;++bankIndex)manifest<<"bank "<<bankIndex<<'\n';
            for(size_t slot=0;slot<16;++slot) {
                const auto& sample=bank->slots[slot];const auto filename="B"+std::to_string(slot/4+1)+"S"+std::to_string(slot%4+1)+".WAV";
                writeCardWav(directory/filename,sample);
                manifest<<"slot "<<slot<<' '<<sample.playback.loop<<' '<<sample.playback.bpm<<'\n';
            }
            manifest.close();if(!manifest)throw std::runtime_error("Card manifest write failed");
        }
        if(std::filesystem::exists(std::filesystem::symlink_status(destination)))throw std::runtime_error("Card destination appeared during export");
        std::filesystem::rename(staging,destination);created=false;
    } catch(...) {if(created) {std::error_code ignored;std::filesystem::remove_all(staging,ignored);}throw;}
}
}
