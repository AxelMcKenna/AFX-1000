#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

namespace rmx {
// Incremental onset autocorrelation. At most one lag is evaluated per 5 ms hop.
// No allocation, worker scheduling, or complete-window scan in one callback.
class TempoTracker {
  public:
    void prepare(double rate) noexcept {
        sr = rate;
        lowAlpha = static_cast<float>(1 - std::exp(-2 * 3.141592653589793 * 250 / rate));
        hop = std::max(1, static_cast<int>(std::round(rate / 200)));
        tickRate = rate / hop;
        minLag = static_cast<int>(std::ceil(60 * tickRate / 180));
        maxLag = static_cast<int>(std::floor(60 * tickRate / 70));
        reset();
    }
    void reset() noexcept {
        novelty.fill(0);
        head = 0;
        age = 0;
        samples = 0;
        energy = 0;
        previous = 0;
        mean = 0;
        lag = minLag;
        best = 0;
        bestLag = 100;
        tempo = 120;
        confidence = 0;
        low = 0;
        lowRight = 0;
    }
    void process(float left, float right) noexcept {
        low += (left - low) * lowAlpha;
        lowRight += (right - lowRight) * lowAlpha;
        energy += (low * low + lowRight * lowRight) * .5f + .04f * (left * left + right * right);
        if (++samples < hop)
            return;
        const float level = std::sqrt(energy / hop);
        energy = 0;
        samples = 0;
        mean += (level - mean) * .025f;
        novelty[head] = std::min(4.f, std::max(0.f, level - previous) / (mean + .003f));
        previous = level;
        head = (head + 1) % novelty.size();
        ++age;
        if (age < 400)
            return;
        const size_t window = std::min(age, novelty.size());
        if (window > static_cast<size_t>(lag * 2)) {
            double sum = 0, a2 = 0, b2 = 0;
            for (size_t i = static_cast<size_t>(lag); i < window; ++i) {
                const float a = novelty[(head + novelty.size() - 1 - i) % novelty.size()];
                const float b =
                    novelty[(head + novelty.size() - 1 - i + static_cast<size_t>(lag)) % novelty.size()];
                sum += a * b;
                a2 += a * a;
                b2 += b * b;
            }
            const double correlation = sum / std::sqrt(a2 * b2 + 1.e-12);
            const double candidate = 60 * tickRate / lag;
            // A light tempo prior resolves otherwise ambiguous half/double-time peaks.
            const double prior = .85 + .15 * std::exp(-std::pow(std::log2(candidate / 120), 2) * 2);
            const float score = static_cast<float>(correlation * prior);
            // Prefer the first strong periodic peak over its slower harmonic repeats.
            if (score > best * 1.12f) {
                best = score;
                bestLag = lag;
            }
        }
        if (++lag > maxLag) {
            const float candidate = static_cast<float>(60 * tickRate / bestLag);
            if (best > .15f && mean > .002f) {
                tempo = confidence < .1f ? candidate : tempo + (candidate - tempo) * .35f;
                confidence = std::clamp(best, 0.f, 1.f);
            } else
                confidence *= .8f;
            lag = minLag;
            best = 0;
        }
    }
    float bpm() const noexcept {
        return tempo;
    }
    float certainty() const noexcept {
        return confidence;
    }

  private:
    std::array<float, 1600> novelty{};
    size_t head{}, age{};
    int hop{240}, samples{}, lag{67}, bestLag{100}, minLag{67}, maxLag{171};
    double sr{48000}, tickRate{200};
    float energy{}, previous{}, mean{}, low{}, lowRight{}, lowAlpha{.032f}, best{}, tempo{120}, confidence{};
};
} // namespace rmx
