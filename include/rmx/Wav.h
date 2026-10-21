#pragma once
#include "Engine.h"
#include <filesystem>
namespace rmx {
Sample readWav(const std::filesystem::path&, double maxSeconds=30);
void writeWav(const std::filesystem::path&, const Sample&);
}
