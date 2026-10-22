#pragma once
#include "Engine.h"
#include <filesystem>
namespace rmx {
Sample readWav(const std::filesystem::path&, double maxSeconds=30);
void writeWav(const std::filesystem::path&, const Sample&);
// Original hardware sample format: 48 kHz stereo signed 24-bit PCM.
void writeCardWav(const std::filesystem::path&,const Sample&);
}
