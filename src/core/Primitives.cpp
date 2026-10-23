#include "rmx/dsp/Primitives.h"
namespace rmx::dsp {
Stereo Delay::read(double ago) const noexcept {
    ago = std::clamp(ago, 1., static_cast<double>(buffer.size() - 2));
    double pos = static_cast<double>(head) - ago;
    if (pos < 0)
        pos += buffer.size();
    const auto index = static_cast<size_t>(pos);
    return mix(buffer[index], buffer[(index + 1) % buffer.size()], static_cast<float>(pos - index));
}
} // namespace rmx::dsp
