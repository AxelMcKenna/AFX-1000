#include "rmx/Engine.h"
#include <array>
#include <chrono>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

// Continuous engine processing with bounded memory. This exercises state carry
// between changes; repeatedly restarting rmx_render would miss those failures.
int main(int argc, char** argv) {
    try {
        double seconds = 7200;
        double rate = 48000;
        for (int i = 1; i < argc; ++i) {
            const std::string arg = argv[i];
            if (arg == "--seconds" && i + 1 < argc) seconds = std::stod(argv[++i]);
            else if (arg == "--rate" && i + 1 < argc) rate = std::stod(argv[++i]);
            else if (arg == "--help") {
                std::cout << "rmx_soak [--seconds 7200] [--rate 48000]\n"
                             "Offline continuous DSP stress, not a device or DAW soak.\n";
                return 0;
            } else throw std::runtime_error("Unknown or incomplete argument: " + arg);
        }
        if (!std::isfinite(seconds) || seconds <= 0 || seconds > 86400 ||
            (rate != 44100 && rate != 48000 && rate != 88200 && rate != 96000))
            throw std::runtime_error("Duration must be 0-86400 seconds and rate 44100/48000/88200/96000");
        constexpr uint32_t maximumBlock = 1024;
        constexpr std::array<uint32_t, 9> blocks{1, 17, 64, 127, 128, 255, 256, 511, 1024};
        auto bank = rmx::makeFactoryBank(rate);
        rmx::Engine engine;
        engine.setBank(&bank);
        engine.prepare(rate, maximumBlock);
        engine.params.set(rmx::Param::AutoTempo, 1);
        std::array<float, maximumBlock> l{}, r{}, ol{}, orr{};
        uint64_t frame = 0, callbacks = 0, nextChange = 0, nextPad = 0, switches = 0;
        uint64_t aboveUnity = 0, deadlineMisses = 0;
        const auto target = static_cast<uint64_t>(seconds * rate);
        uint32_t rng = 0x524d5831;
        auto random = [&] { rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5; return rng; };
        double energy = 0, peak = 0, maximumLoad = 0;
        std::array<uint64_t, 1001> loadHistogram{};
        const auto start = std::chrono::steady_clock::now();
        while (frame < target) {
            const auto n = static_cast<uint32_t>(std::min<uint64_t>(blocks[random() % blocks.size()], target - frame));
            if (frame >= nextChange) {
                const auto scene = switches % 10;
                engine.params.set(rmx::Param::SceneType, static_cast<float>(scene));
                engine.params.set(rmx::Param::SceneOn, (switches % 13) != 0);
                engine.params.set(rmx::Param::SceneDepth, static_cast<float>((switches % 5) * .25));
                engine.params.set(rmx::Param::SceneTime, static_cast<float>(switches % 8));
                engine.params.set(rmx::Param::SceneSource, static_cast<float>(switches % 4));
                engine.params.set(rmx::Param::IsolateMode, static_cast<float>((switches / 10) % 4));
                engine.params.set(rmx::Param::IsolateOn, switches % 7 != 0);
                for (auto p : {rmx::Param::Low, rmx::Param::Mid, rmx::Param::High})
                    engine.params.set(p, static_cast<float>(static_cast<int>(random() % 201) - 100) / 100);
                engine.params.set(rmx::Param::ReleaseType, static_cast<float>((switches / 3) % 3));
                engine.params.set(rmx::Param::ReleaseAmount, switches % 11 == 0 ? .9f : 0.f);
                engine.params.set(rmx::Param::Bypass, switches % 17 == 0);
                engine.params.set(rmx::Param::XSource, static_cast<float>((switches / 7) % 2));
                engine.params.set(rmx::Param::Overdub, switches % 7 == 0);
                if (switches % 5 == 0) engine.enqueue({rmx::EventType::RollStart, 0});
                else engine.enqueue({rmx::EventType::RollStop});
                if (switches % 19 == 0) engine.enqueue({rmx::EventType::ClearSequence});
                ++switches;
                nextChange += static_cast<uint64_t>(rate);
            }
            if (frame >= nextPad) {
                for (uint8_t pad = 0; pad < 4; ++pad)
                    engine.enqueue({rmx::EventType::Trigger, pad, .8f});
                nextPad += static_cast<uint64_t>(rate / 4);
            }
            for (uint32_t i = 0; i < n; ++i) {
                const double t = (frame + i) / rate;
                const double envelope = std::exp(-std::fmod(t, .5) * 25);
                const float noise = (static_cast<int32_t>(random() & 0xffff) - 32768) / 32768.f * .015f;
                l[i] = static_cast<float>(.25 * std::sin(t * 2 * 3.141592653589793 * 73) * envelope) + noise;
                r[i] = static_cast<float>(.2 * std::sin(t * 2 * 3.141592653589793 * 317) * envelope) - noise;
            }
            const auto tick = std::chrono::steady_clock::now();
            engine.process(l.data(), r.data(), ol.data(), orr.data(), n);
            const double load = std::chrono::duration<double>(std::chrono::steady_clock::now() - tick).count() / (n / rate);
            maximumLoad = std::max(maximumLoad, load);
            deadlineMisses += load > 1;
            ++loadHistogram[std::min<size_t>(1000, static_cast<size_t>(load * 1000))];
            for (uint32_t i = 0; i < n; ++i) {
                if (!std::isfinite(ol[i]) || !std::isfinite(orr[i])) throw std::runtime_error("Non-finite output at frame " + std::to_string(frame + i));
                for (float sample : {ol[i], orr[i]}) {
                    peak = std::max(peak, std::abs(static_cast<double>(sample)));
                    energy += sample * sample;
                    aboveUnity += std::abs(sample) > 1;
                }
            }
            frame += n;
            ++callbacks;
        }
        uint64_t sum = 0;
        size_t p99 = 1000;
        for (size_t i = 0; i < loadHistogram.size(); ++i) {
            sum += loadHistogram[i];
            if (sum >= static_cast<uint64_t>(std::ceil(callbacks * .99))) { p99 = i; break; }
        }
        const auto elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
        std::cout << "{\n  \"kind\": \"offline-continuous-engine-soak\",\n"
                  << "  \"sample_rate\": " << rate << ",\n  \"processed_frames\": " << frame
                  << ",\n  \"simulated_seconds\": " << frame / rate << ",\n  \"wall_seconds\": " << elapsed
                  << ",\n  \"callbacks\": " << callbacks << ",\n  \"state_changes\": " << switches
                  << ",\n  \"peak\": " << peak << ",\n  \"rms\": " << std::sqrt(energy / (2 * frame))
                  << ",\n  \"samples_above_unity\": " << aboveUnity
                  << ",\n  \"dropped_events\": " << engine.meters.droppedEvents.load()
                  << ",\n  \"callbacks_over_deadline\": " << deadlineMisses
                  << ",\n  \"maximum_deadline_fraction\": " << maximumLoad
                  << ",\n  \"p99_deadline_fraction_upper_bound\": " << (p99 == 1000 ? "null" : std::to_string((p99 + 1) / 1000.))
                  << ",\n  \"limitations\": \"No device I/O, DAW, memory-leak measurement or real-time scheduling validation. Histogram saturates at a deadline fraction of 1.\"\n}\n";
        // Engine output protection intentionally permits a soft bounded region
        // up to 1.25. Samples above digital unity remain visible in the report.
        return engine.meters.droppedEvents.load() == 0 && peak <= 1.2501 ? 0 : 2;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
