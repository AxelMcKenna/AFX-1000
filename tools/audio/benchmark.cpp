#include "rmx/Engine.h"
#include <charconv>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>

namespace {
struct Options {
    unsigned blocks{2000}, rate{}, block{};
    bool quick{}, strictMaximum{};
    std::string csv;
};
unsigned number(std::string_view text) {
    unsigned value{};
    const auto [end, error] = std::from_chars(text.data(), text.data() + text.size(), value);
    if (error != std::errc{} || end != text.data() + text.size() || !value)
        throw std::runtime_error("Expected a positive integer");
    return value;
}
Options options(int argc, char** argv) {
    Options result;
    for (int i = 1; i < argc; ++i) {
        const std::string_view argument(argv[i]);
        if (argument == "--quick")
            result.quick = true;
        else if (argument == "--strict-max")
            result.strictMaximum = true;
        else if (argument == "--csv" || argument == "--rate" || argument == "--block") {
            if (++i == argc)
                throw std::runtime_error("Missing option value");
            if (argument == "--csv")
                result.csv = argv[i];
            else if (argument == "--rate")
                result.rate = number(argv[i]);
            else
                result.block = number(argv[i]);
        } else
            result.blocks = number(argument);
    }
    if (result.blocks < 100 || result.blocks > 1000000 ||
        (result.rate && result.rate != 44100 && result.rate != 48000 && result.rate != 96000) ||
        result.block > 8192)
        throw std::runtime_error("Use 100..1000000 blocks, rate 44100/48000/96000, block 1..8192");
    return result;
}

enum class Kind {
    Neutral,
    Bypass,
    Scene,
    Drive,
    IsolateRoll,
    Capture,
    Voices,
    Release,
    Events,
    Automation,
    AutoTempo,
    Variable,
    SilenceTail,
    Combined
};
struct Workload {
    std::string name;
    Kind kind;
    int choice{};
};
std::vector<Workload> workloads() {
    std::vector<Workload> result{{"neutral", Kind::Neutral}, {"bypass", Kind::Bypass}};
    for (size_t i = 0; i < rmx::sceneNames.size(); ++i)
        result.push_back({std::string(rmx::sceneNames[i]), Kind::Scene, static_cast<int>(i)});
    result.insert(result.end(), {{"drive", Kind::Drive},
                                 {"isolator_roll_bursts", Kind::IsolateRoll},
                                 {"capture_roll_bursts", Kind::Capture},
                                 {"32_voices", Kind::Voices},
                                 {"backspin", Kind::Release, 0},
                                 {"release_echo", Kind::Release, 1},
                                 {"vinyl_brake", Kind::Release, 2},
                                 {"dense_events", Kind::Events},
                                 {"automation", Kind::Automation},
                                 {"auto_tempo", Kind::AutoTempo},
                                 {"variable_blocks", Kind::Variable},
                                 {"reverb_silence_tail", Kind::SilenceTail},
                                 {"combined_fx", Kind::Combined}});
    return result;
}

void configure(rmx::Engine& engine, const Workload& work) {
    for (size_t i = 0; i < rmx::parameterCount; ++i)
        engine.params.set(static_cast<rmx::Param>(i), rmx::parameters[i].initial);
    auto set = [&](rmx::Param p, float value) { engine.params.set(p, value); };
    set(rmx::Param::Quantize, 0);
    if (work.kind == Kind::Bypass)
        set(rmx::Param::Bypass, 1);
    if (work.kind == Kind::Scene || work.kind == Kind::Automation || work.kind == Kind::SilenceTail ||
        work.kind == Kind::Combined) {
        set(rmx::Param::SceneOn, 1);
        set(rmx::Param::SceneDepth, 1);
        set(rmx::Param::SceneType, work.kind == Kind::SilenceTail ? 4.f : static_cast<float>(work.choice));
    }
    if (work.kind == Kind::Drive || work.kind == Kind::IsolateRoll || work.kind == Kind::Combined) {
        set(rmx::Param::IsolateMode, work.kind == Kind::Drive ? 3.f : 2.f);
        for (auto p : {rmx::Param::Low, rmx::Param::Mid, rmx::Param::High})
            set(p, .8f);
    }
    if (work.kind == Kind::Capture || work.kind == Kind::Combined) {
        set(rmx::Param::XSource, 1);
        set(rmx::Param::XRoll, 7);
    }
    if (work.kind == Kind::Release || work.kind == Kind::Combined) {
        set(rmx::Param::ReleaseAmount, 1);
        set(rmx::Param::ReleaseType, static_cast<float>(work.choice));
    }
    if (work.kind == Kind::AutoTempo)
        set(rmx::Param::AutoTempo, 1);
    engine.reset();
}

double percentile(const std::vector<double>& sorted, double fraction) {
    return sorted[std::min(sorted.size() - 1, static_cast<size_t>(sorted.size() * fraction))];
}

bool measure(rmx::Engine& engine, double rate, unsigned block, const Workload& work, const Options& opts,
             std::ostream* csv) {
    configure(engine, work);
    std::vector<float> left(block), right(block), outL(block), outR(block);
    for (unsigned i = 0; i < block; ++i) {
        left[i] = std::sin(i * .13f) * .2f;
        right[i] = std::cos(i * .11f) * .17f;
    }
    std::vector<double> times, loads;
    times.reserve(opts.blocks);
    loads.reserve(opts.blocks);
    const auto warmup =
        std::max(256u, static_cast<unsigned>(rate * (work.kind == Kind::AutoTempo ? 9 : .15) / block));
    unsigned misses = 0;
    std::array<rmx::Event, 256> events;
    for (size_t i = 0; i < events.size(); ++i)
        events[i] = {rmx::EventType::Trigger, static_cast<uint8_t>(i % 4), .02f,
                     static_cast<uint32_t>(i * block / events.size())};
    for (unsigned n = 0; n < warmup + opts.blocks; ++n) {
        if (work.kind == Kind::Voices && n % 8 == 0)
            for (unsigned pad = 0; pad < 32; ++pad)
                engine.enqueue({rmx::EventType::Trigger, 0, .025f});
        if (work.kind == Kind::Capture && n % 16 == 0)
            engine.enqueue({rmx::EventType::Trigger});
        if (work.kind == Kind::Combined) {
            if (n % 16 == 0) {
                engine.params.set(rmx::Param::XSource, 0);
                for (unsigned pad = 0; pad < 32; ++pad)
                    engine.enqueue({rmx::EventType::Trigger, 0, .025f});
            } else if (n % 16 == 1) {
                engine.params.set(rmx::Param::XSource, 1);
                engine.enqueue({rmx::EventType::Trigger});
            }
            if (n % 32 == 0) {
                engine.params.set(rmx::Param::SceneType, static_cast<float>((n / 32) % 10));
                for (auto p : {rmx::Param::Low, rmx::Param::Mid, rmx::Param::High})
                    engine.params.set(p, (n / 32) % 2 ? .3f : .8f);
            }
        }
        if (work.kind == Kind::IsolateRoll && n % 32 == 0)
            engine.params.set(rmx::Param::Low, (n / 32) % 2 ? .3f : .8f);
        if (work.kind == Kind::Automation && n % 8 == 0) {
            engine.params.set(rmx::Param::SceneType, static_cast<float>((n / 8) % 10));
            engine.params.set(rmx::Param::SceneDepth, (n / 8) % 2 ? .1f : 1.f);
            engine.params.set(rmx::Param::InputGain, (n / 8) % 2 ? -12.f : 6.f);
            engine.params.set(rmx::Param::XPitch, (n / 8) % 2 ? -24.f : 24.f);
        }
        if (work.kind == Kind::SilenceTail && n == warmup) {
            std::fill(left.begin(), left.end(), 0);
            std::fill(right.begin(), right.end(), 0);
        }
        const unsigned frames = work.kind != Kind::Variable ? block
                                : n % 3 == 0                ? 1
                                : n % 3 == 1                ? std::max(1u, block - 1)
                                                            : block;
        const auto direct =
            work.kind == Kind::Events ? std::span<const rmx::Event>(events) : std::span<const rmx::Event>{};
        const auto start = std::chrono::steady_clock::now();
        engine.process(left.data(), right.data(), outL.data(), outR.data(), frames, {}, direct);
        const double us =
            std::chrono::duration<double, std::micro>(std::chrono::steady_clock::now() - start).count();
        if (n >= warmup) {
            const double load = us / (frames / rate * 1.e6) * 100;
            times.push_back(us);
            loads.push_back(load);
            misses += load >= 100;
        }
    }
    std::sort(times.begin(), times.end());
    std::sort(loads.begin(), loads.end());
    const double mean = std::accumulate(times.begin(), times.end(), 0.) / times.size();
    std::cout << static_cast<unsigned>(rate) << '/' << block << ' ' << work.name << ": mean " << mean
              << " us; p99 " << percentile(loads, .99) << "%, p99.9 " << percentile(loads, .999) << "%, max "
              << loads.back() << "% deadline; misses " << misses << '\n';
    if (csv)
        *csv << static_cast<unsigned>(rate) << ',' << block << ',' << work.name << ',' << opts.blocks << ','
             << mean << ',' << percentile(times, .99) << ',' << percentile(times, .999) << ',' << times.back()
             << ',' << percentile(loads, .99) << ',' << percentile(loads, .999) << ',' << loads.back() << ','
             << misses << '\n';
    return percentile(loads, .99) < 50 && (!opts.strictMaximum || misses == 0);
}
} // namespace

int main(int argc, char** argv) {
    try {
        const auto opts = options(argc, argv);
        std::ofstream csv;
        if (!opts.csv.empty()) {
            csv.open(opts.csv);
            if (!csv)
                throw std::runtime_error("Cannot create benchmark CSV");
            csv << "sample_rate,max_block,workload,blocks,mean_us,p99_us,p999_us,max_us,p99_deadline_pct,"
                   "p999_deadline_pct,max_deadline_pct,deadline_misses\n";
        }
        std::cout << std::fixed << std::setprecision(3);
        bool passed = true;
        for (unsigned rate : {44100u, 48000u, 96000u}) {
            if ((opts.rate && opts.rate != rate) || (!opts.rate && opts.quick && rate != 48000))
                continue;
            auto bank = rmx::makeFactoryBank(rate);
            for (unsigned block : opts.block   ? std::vector<unsigned>{opts.block}
                                  : opts.quick ? std::vector<unsigned>{128}
                                               : std::vector<unsigned>{32, 128, 512}) {
                rmx::Engine engine;
                engine.setBank(&bank);
                engine.prepare(rate, block);
                for (const auto& work : workloads())
                    passed =
                        measure(engine, rate, block, work, opts, csv.is_open() ? &csv : nullptr) && passed;
            }
        }
        if (csv.is_open()) {
            csv.flush();
            if (!csv)
                throw std::runtime_error("Cannot write benchmark CSV");
        }
        std::cout << "Offline DSP timing only. Gate: p99 < 50% deadline"
                  << (opts.strictMaximum ? ", no wall-time overruns" : "; max and misses reported, not gated")
                  << ". Live audio and MCU timing require separate measurement.\n";
        return passed ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << error.what()
                  << "\nUsage: rmx_benchmark [blocks] [--quick] [--rate Hz] [--block frames] [--csv path] "
                     "[--strict-max]\n";
        return 1;
    }
}
