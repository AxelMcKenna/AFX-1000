#include "rmx/Engine.h"
#include "rmx/State.h"
#include "rmx/Wav.h"
#include "rmx/controls/PanelController.h"
#include <atomic>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <limits>
#include <new>
#include <stdexcept>

static thread_local bool trackAllocations = false;
static thread_local size_t allocationCount = 0;
void* operator new(size_t size) {
    if (trackAllocations)
        ++allocationCount;
    if (void* p = std::malloc(size ? size : 1))
        return p;
    throw std::bad_alloc();
}
void operator delete(void* p) noexcept {
    std::free(p);
}
void* operator new[](size_t size) {
    return ::operator new(size);
}
void operator delete[](void* p) noexcept {
    std::free(p);
}

namespace {
void require(bool condition, const char* message) {
    if (!condition)
        throw std::runtime_error(message);
}
struct Rig {
    rmx::SampleBank bank = rmx::makeFactoryBank();
    rmx::Engine engine;
    std::array<float, 256> l{}, r{}, ol{}, orr{};
    Rig(double sr = 48000) {
        engine.setBank(&bank);
        engine.prepare(sr, 256);
    }
    double run(int blocks) {
        double energy = 0;
        for (int b = 0; b < blocks; ++b) {
            engine.process(l.data(), r.data(), ol.data(), orr.data(), 256);
            for (float v : ol) {
                require(std::isfinite(v), "Non-finite output");
                energy += v * v;
            }
        }
        return energy;
    }
};

void neutral_stereo() {
    {
        Rig rig;
        for (size_t i = 0; i < 256; ++i) {
            rig.l[i] = std::sin(i * .1f) * .25f;
            rig.r[i] = std::cos(i * .07f) * .2f;
        }
        rig.run(10);
        for (size_t i = 0; i < 256; ++i) {
            require(std::abs(rig.l[i] - rig.ol[i]) < 1e-5, "Neutral stereo left differs");
            require(std::abs(rig.r[i] - rig.orr[i]) < 1e-5, "Neutral stereo right differs");
        }
        rig.engine.params.set(rmx::Param::WetOnly, 1);
        rig.run(10);
        for (float v : rig.ol)
            require(std::abs(v) < 1e-5, "Wet-only neutral must null");
    }
}

void sampler_panic() {
    {
        Rig rig;
        rig.engine.params.set(rmx::Param::Quantize, 0);
        rig.engine.enqueue({rmx::EventType::Trigger, 0});
        require(rig.run(100) > 1, "Factory sampler is silent");
        rig.engine.enqueue({rmx::EventType::Panic});
        require(rig.run(100) < 1e-8, "Panic did not stop sampler");
    }
}

void echo_tail() {
    {
        Rig rig;
        rig.engine.params.set(rmx::Param::SceneOn, 1);
        rig.engine.params.set(rmx::Param::SceneDepth, 1);
        rig.engine.params.set(rmx::Param::SceneType, 1);
        rig.run(10);
        rig.l[0] = rig.r[0] = .5;
        rig.run(1);
        rig.l.fill(0);
        rig.r.fill(0);
        require(rig.run(100) > .01, "Echo produced no tail");
    }
}

void effect_extremes() {
    for (double rate : {44100., 48000., 88200., 96000.}) {
        Rig rig(rate);
        for (size_t i = 0; i < 256; ++i)
            rig.l[i] = rig.r[i] = std::sin(i * .2f) * .4f;
        for (int scene = 0; scene < 10; ++scene)
            for (int mode = 0; mode < 4; ++mode) {
                rig.engine.params.set(rmx::Param::SceneType, static_cast<float>(scene));
                rig.engine.params.set(rmx::Param::SceneOn, 1);
                rig.engine.params.set(rmx::Param::SceneDepth, 1);
                rig.engine.params.set(rmx::Param::IsolateMode, static_cast<float>(mode));
                rig.engine.params.set(rmx::Param::Low, -1);
                rig.engine.params.set(rmx::Param::Mid, 1);
                rig.engine.params.set(rmx::Param::High, 1);
                rig.run(15);
            }
        for (int release = 0; release < 3; ++release) {
            rig.engine.params.set(rmx::Param::ReleaseType, static_cast<float>(release));
            rig.engine.params.set(rmx::Param::ReleaseAmount, 1);
            rig.run(200);
            rig.engine.params.set(rmx::Param::ReleaseAmount, 0);
            rig.run(1);
            require(rig.engine.params.get(rmx::Param::SceneOn) == 0, "Release did not reset scene");
            require(rig.engine.params.get(rmx::Param::Low) == 0, "Release did not reset isolator");
        }
        rig.l[0] = std::numeric_limits<float>::quiet_NaN();
        rig.r[0] = std::numeric_limits<float>::infinity();
        rig.run(1);
    }
}

void scene_processing() {
    for (int scene = 0; scene < 10; ++scene) {
        Rig rig;
        rig.engine.params.set(rmx::Param::SceneOn, 1);
        rig.engine.params.set(rmx::Param::SceneDepth, .8f);
        rig.engine.params.set(rmx::Param::SceneType, static_cast<float>(scene));
        double difference = 0;
        uint32_t rng = 12345;
        for (int block = 0; block < 450; ++block) {
            for (size_t i = 0; i < 256; ++i) {
                rng ^= rng << 13;
                rng ^= rng >> 17;
                rng ^= rng << 5;
                rig.l[i] = rig.r[i] = static_cast<float>(static_cast<int32_t>(rng)) / 2147483648.f * .15f;
            }
            rig.run(1);
            for (size_t i = 0; i < 256; ++i)
                difference += std::pow(rig.ol[i] - rig.l[i], 2);
        }
        require(difference > .01, "An enabled Scene FX has no audible processing");
    }
}

void realtime_allocations() {
    {
        Rig rig;
        rig.engine.params.set(rmx::Param::Quantize, 0);
        rig.engine.params.set(rmx::Param::IsolateMode, 2);
        rig.engine.params.set(rmx::Param::Low, 1);
        rig.engine.params.set(rmx::Param::Mid, 1);
        rig.engine.params.set(rmx::Param::High, 1);
        rig.engine.params.set(rmx::Param::XSource, 1);
        rig.engine.enqueue({rmx::EventType::RollStart, 0});
        trackAllocations = true;
        for (int i = 0; i < 1200; ++i)
            rig.engine.process(rig.l.data(), rig.r.data(), rig.ol.data(), rig.orr.data(),
                               static_cast<uint32_t>(i % 3 == 0   ? 1
                                                     : i % 3 == 1 ? 127
                                                                  : 256));
        trackAllocations = false;
        require(allocationCount == 0, "Audio processing allocated memory");
    }
}

void state_roundtrip() {
    {
        rmx::State state;
        state.values[static_cast<size_t>(rmx::Param::SceneType)] = 8;
        state.samplePaths[3] = "/tmp/drum with spaces.wav";
        state.cc[100] = static_cast<int>(rmx::Param::Low);
        auto copy = rmx::State::parse(state.serialize());
        require(copy.samplePaths == state.samplePaths, "Sample references changed");
        require(copy.cc == state.cc, "MIDI mapping changed");
        require(copy.values[static_cast<size_t>(rmx::Param::SceneType)] == 8, "State value changed");
        bool rejected = false;
        try {
            (void)rmx::State::parse("RMX_STATE 99\n");
        } catch (...) {
            rejected = true;
        }
        require(rejected, "Unsupported state accepted");
        rmx::ParameterStore params;
        params.set(rmx::Param::Tempo, std::numeric_limits<float>::quiet_NaN());
        require(params.get(rmx::Param::Tempo) == 120, "Invalid parameter not sanitized");
    }
}

void queue_bounds() {
    {
        rmx::SpscQueue<int, 8> q;
        for (int i = 0; i < 7; ++i)
            require(q.push(i), "Queue filled early");
        require(!q.push(8), "Queue overflow was not rejected");
        int v;
        for (int i = 0; i < 7; ++i)
            require(q.pop(v) && v == i, "Queue lost ordering");
        require(!q.pop(v), "Queue read past end");
    }
}

void panel_actions() {
    {
        Rig rig;
        int events = 0;
        auto read = [&](rmx::Param p) { return rig.engine.params.get(p); };
        auto write = [&](rmx::Param p, float v) { rig.engine.params.set(p, v); };
        auto send = [&](rmx::Event e) {
            ++events;
            rig.engine.enqueue(e);
        };
        for (const auto& c : rmx::panel::controls()) {
            if (c.kind == rmx::panel::Kind::Toggle) {
                const float before = read(c.param);
                require(rmx::panel::activate(c, read, write, send), "Toggle not handled");
                require(read(c.param) != before, "Toggle did not change state");
            }
            if (c.kind == rmx::panel::Kind::Choice) {
                rmx::panel::activate(c, read, write, send);
                require(read(c.param) == c.value, "Choice did not select its mode");
            }
            if (c.kind == rmx::panel::Kind::Pad)
                rmx::panel::activate(c, read, write, send);
            if (c.kind == rmx::panel::Kind::Action && c.action != rmx::panel::Action::None)
                require(rmx::panel::activate(c, read, write, send), "Hardware action not handled");
        }
        require(events >= 5, "Pad or tap failed to dispatch");
        rig.engine.params.set(rmx::Param::SceneSource, 2);
        auto input = rmx::panel::controls()[6];
        for (const auto& c : rmx::panel::controls())
            if (c.action == rmx::panel::Action::ToggleSource && c.value == 0)
                input = c;
        rmx::panel::activate(input, read, write, send);
        require(read(rmx::Param::SceneSource) == 1, "Input source did not switch off");
        rmx::panel::activate(input, read, write, send);
        require(read(rmx::Param::SceneSource) == 2, "Input source did not restore");
        for (int scene = 0; scene < 10; ++scene) {
            const float angle = (scene < 5 ? -140.4f + scene * 25.2f : 140.4f - (scene - 5) * 25.2f) *
                                3.141592653589793f / 180;
            require(rmx::panel::sceneAt(1503 + 250 * std::cos(angle), 466 + 250 * std::sin(angle)) == scene,
                    "Scene wedge hit area does not match its button");
        }
    }
}

void tempo_detection() {
    for (float expected : {90.f, 120.f, 128.f, 150.f, 173.f}) {
        rmx::TempoTracker tracker;
        tracker.prepare(48000);
        for (int i = 0; i < 48000 * 14; ++i) {
            const double phase = std::fmod(i / 48000., 60. / expected);
            const float kick =
                static_cast<float>(std::sin(2 * 3.141592653589793 * 70 * phase) * std::exp(-phase * 35)) *
                .7f;
            tracker.process(kick, kick);
        }
        std::cout << "Auto BPM " << expected << " -> " << tracker.bpm() << " (confidence "
                  << tracker.certainty() << ")\n";
        require(std::abs(tracker.bpm() - expected) < 2.5f, "Auto BPM did not find the test rhythm");
        require(tracker.certainty() > .15f, "Auto BPM failed to lock");
    }
}

void wav_roundtrip() {
    {
        rmx::Sample input;
        input.frames = {{.125f, -.25f}, {0, 1}, {-.75f, .5f}};
        auto path = std::filesystem::temp_directory_path() /
                    ("rmx-roundtrip-" +
                     std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()) + ".wav");
        rmx::writeWav(path, input);
        auto output = rmx::readWav(path);
        std::filesystem::remove(path);
        require(output.frames.size() == input.frames.size(), "WAV length changed");
        for (size_t i = 0; i < input.frames.size(); ++i)
            require(input.frames[i].l == output.frames[i].l && input.frames[i].r == output.frames[i].r,
                    "Float WAV did not roundtrip");
    }
}

} // namespace
int main(int argc, char** argv) {
    struct Case {
        const char* name;
        void (*run)();
    };
    const Case cases[]{
        {"neutral_stereo", neutral_stereo},
        {"sampler_panic", sampler_panic},
        {"echo_tail", echo_tail},
        {"effect_extremes", effect_extremes},
        {"scene_processing", scene_processing},
        {"realtime_allocations", realtime_allocations},
        {"state_roundtrip", state_roundtrip},
        {"queue_bounds", queue_bounds},
        {"panel_actions", panel_actions},
        {"tempo_detection", tempo_detection},
        {"wav_roundtrip", wav_roundtrip},
    };
    bool matched = false;
    for (const auto& test : cases) {
        if (argc > 1 && std::string_view(argv[1]) != test.name)
            continue;
        matched = true;
        try {
            test.run();
            std::cout << "PASS: " << test.name << '\n';
        } catch (const std::exception& e) {
            std::cerr << "FAIL: " << test.name << ": " << e.what() << '\n';
            return 1;
        }
    }
    if (!matched) {
        std::cerr << "Unknown test case\n";
        return 2;
    }
}
