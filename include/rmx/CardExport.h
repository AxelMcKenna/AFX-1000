#pragma once
#include "State.h"
namespace rmx {
enum class CardExportMode { All,UserOnly,SamplesOnly };
// Write a new directory containing RMX/USER.TXT, SAMPLES.TXT and WAVs.
// Does not alter an existing card/directory; paths resolve relative to the preset.
void exportCardSamples(const State&,const std::filesystem::path& presetDirectory,const std::filesystem::path& destination,CardExportMode mode=CardExportMode::All);
}
