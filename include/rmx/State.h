#pragma once
#include "Parameters.h"
#include "Sample.h"
#include <filesystem>
#include <string>

namespace rmx {
struct State {
    std::array<float,parameterCount> values{};
    std::array<std::string,16> samplePaths{};
    std::array<SamplePlayback,16> samplePlayback{};
    std::array<int,128> cc{};
    State();
    void capture(const ParameterStore&);
    void apply(ParameterStore&) const;
    void applySamples(SampleBank&) const;
    void captureSamples(const SampleBank&);
    std::string serialize() const;
    static State parse(std::string_view);
    void save(const std::filesystem::path&) const;
    static State load(const std::filesystem::path&);
};
}
