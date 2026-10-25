#include "rmx/dsp/Primitives.h"
namespace rmx {
using dsp::pi;
SampleBank makeFactoryBank(double rate) {
    SampleBank bank;
    for (int slot = 0; slot < 16; ++slot) {
        auto& s = bank.slots[static_cast<size_t>(slot)];
        s.rate = rate;
        const int type = slot % 4, variation = slot / 4;
        const double length = type == 0 ? .7 : type == 1 ? .38 : type == 2 ? .32 : .16;
        s.frames.resize(static_cast<size_t>(rate * length));
        uint32_t random = 0x749abc + static_cast<uint32_t>(slot);
        double phase = 0;
        float low = 0;
        for (size_t i = 0; i < s.frames.size(); ++i) {
            double t = i / rate;
            random ^= random << 13;
            random ^= random >> 17;
            random ^= random << 5;
            const float n = static_cast<float>(static_cast<int32_t>(random)) / 2147483648.f;
            phase += 2 * pi * (45 + variation * 6 + 100 * std::exp(-t * 35)) / rate;
            low += .2f * (n - low);
            float value = 0;
            if (type == 0)
                value = static_cast<float>(std::sin(phase) * std::exp(-t * (8 + variation)) * .85 +
                                           n * std::exp(-t * 220) * .15);
            if (type == 1)
                value = static_cast<float>(n * std::exp(-t * 20) * .55 +
                                           std::sin(2 * pi * (170 + variation * 20) * t) * std::exp(-t * 28) *
                                               .3);
            if (type == 2) {
                double pulse = std::fmod(t, .011);
                value =
                    static_cast<float>((n - low) * std::exp(-t * 20) * (.35 + .3 * std::exp(-pulse * 300)));
            }
            if (type == 3)
                value = static_cast<float>((n - low) * std::exp(-t * (45 - variation * 5)) * .5);
            s.frames[i] = {value, value};
        }
    }
    return bank;
}
} // namespace rmx
