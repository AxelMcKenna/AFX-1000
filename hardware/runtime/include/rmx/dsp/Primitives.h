#pragma once
#include "rmx/AudioTypes.h"
#include "rmx/Parameters.h"
#include <limits>
#include <numbers>

namespace rmx::dsp {
inline constexpr float pi = std::numbers::pi_v<float>;
// Recompute nonlinear control transforms only while their input changes. Keep
// sample-by-sample smoothing; reset caches when the sample rate changes.
template <class T> class CachedValue {
  public:
    template <class Transform> T get(T value, Transform transform) noexcept {
        if (value != input) {
            input = value;
            output = transform(value);
        }
        return output;
    }

  private:
    T input{std::numeric_limits<T>::quiet_NaN()}, output{};
};
inline float db(float x) noexcept {
    return std::pow(10.f, x / 20.f);
}
inline float coefficient(float hz, double sr) noexcept {
    return 1 - std::exp(-2 * pi * hz / static_cast<float>(sr));
}
inline Stereo finite(Stereo x) noexcept {
    return {std::isfinite(x.l) ? std::clamp(x.l, -16.f, 16.f) : 0,
            std::isfinite(x.r) ? std::clamp(x.r, -16.f, 16.f) : 0};
}
inline float level(Stereo x) noexcept {
    return std::max(std::abs(x.l), std::abs(x.r));
}
struct Context {
    const std::array<float, parameterCount>& values;
    const std::array<float, parameterCount>& smoothed;
    double sr, bpm, beat;
    uint64_t frame;
    float smoothing;
    float get(Param p) const noexcept {
        return values[static_cast<size_t>(p)];
    }
    float sm(Param p) const noexcept {
        return smoothed[static_cast<size_t>(p)];
    }
};
class Delay {
  public:
    void prepare(size_t n) {
        buffer.assign(n, {});
        head = 0;
    }
    void clear() noexcept {
        std::fill(buffer.begin(), buffer.end(), Stereo{});
        head = 0;
    }
    Stereo read(double ago) const noexcept;
    void push(Stereo v) noexcept {
        buffer[head] = v;
        if (++head == buffer.size())
            head = 0;
    }

  private:
    std::vector<Stereo> buffer;
    size_t head{};
};
struct Filter {
    Stereo z{};
    Stereo low(Stereo in, float a) noexcept {
        z = z + (in - z) * a;
        return z;
    }
};
} // namespace rmx::dsp
