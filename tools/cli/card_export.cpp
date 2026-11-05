#include "rmx/CardExport.h"
#include <iostream>
#include <stdexcept>
int main(int argc,char** argv) {
    if(argc!=3&&argc!=4) {std::cerr<<"Usage: rmx_card_export preset.rmx new-output-directory [--settings-only|--samples-only]\n";return 1;}
    try {
        auto mode=rmx::CardExportMode::All;
        if(argc==4) {
            const std::string_view option=argv[3];
            if(option=="--settings-only")mode=rmx::CardExportMode::UserOnly;
            else if(option=="--samples-only")mode=rmx::CardExportMode::SamplesOnly;
            else throw std::runtime_error("Unknown card export option");
        }
        const std::filesystem::path preset=argv[1];rmx::exportCardSamples(rmx::State::load(preset),preset.parent_path(),argv[2],mode);
        std::cout<<"Exported RMX card data. Copy the RMX folder to a FAT-formatted card; this project layout is not Pioneer RSD/SD format.\n";
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
