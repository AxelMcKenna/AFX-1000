#pragma once
#include "Primitives.h"
namespace rmx::dsp {
class Isolator {
  public:
    void prepare(double sampleRate);
    void reset() noexcept;
    void configure(float lowHz, float highHz, double sampleRate) noexcept;
    Stereo process(Stereo x, size_t bus, const Context& ctx) noexcept;

  private:
    struct BandLoop {
        Delay history;
        std::vector<Stereo> frozen;
        size_t length{}, copied{};
        uint64_t start{};
        double position{};
        bool active{};
    };
    std::array<std::array<BandLoop, 3>, 2> bandLoops;
    std::array<Filter, 2> lowSplit, highSplit;
    float lowAlpha{}, highAlpha{};
};
} // namespace rmx::dsp
