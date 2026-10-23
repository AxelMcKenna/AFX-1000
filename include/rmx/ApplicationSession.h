#pragma once
#include "Engine.h"
#include "State.h"
#include "Wav.h"
#include <chrono>
#include <functional>
#include <stdexcept>

namespace rmx {
struct AudioConfiguration {
    uint32_t input{}, output{}, inputPair{}, outputPair{}, bufferFrames{128};
    bool applicationCapture{};
};
struct SampleInfo {
    double duration{};
    size_t frames{};
};
struct SampleEdit {
    double begin{}, end{};
    bool normalize{}, reverse{};
};

// All workflow methods have one control-thread owner. The native controller
// serializes access; only atomic parameters/meters are shared with the UI.
// Host is injected so lifecycle and asset transactions can be tested headlessly.
template <class Host> class ApplicationSession {
  public:
    Engine engine;
    Host host;

    explicit ApplicationSession(std::filesystem::path sessionPath)
        : host(engine), bank(makeFactoryBank()), sessionPath(std::move(sessionPath)) {
        engine.setBank(&bank);
        engine.prepare(48000, 8192);
    }
    ~ApplicationSession() {
        host.stop();
    }

    void start(AudioConfiguration configuration) {
        route = configuration;
        std::string error;
        const bool ok = route.applicationCapture
                            ? host.startRekordbox(route.output, route.outputPair, route.bufferFrames, error)
                            : host.start(route.input, route.output, route.inputPair, route.outputPair,
                                         route.bufferFrames, error);
        if (!ok)
            throw std::runtime_error(error);
    }
    void stop() {
        host.stop();
    }
    void save(const std::filesystem::path& path) {
        state.capture(engine.params);
        for (size_t i = 0; i < state.cc.size(); ++i)
            state.cc[i] = host.midiControls.cc[i].load();
        state.save(path);
    }
    void persist() {
        std::filesystem::create_directories(sessionPath.parent_path());
        save(sessionPath);
    }
    std::string restoreSession() {
        if (!std::filesystem::exists(sessionPath))
            return {};
        return load(sessionPath);
    }
    std::string load(const std::filesystem::path& path) {
        auto next = State::load(path);
        auto assets = makeFactoryBank();
        std::string missing;
        for (size_t i = 0; i < next.samplePaths.size(); ++i) {
            if (next.samplePaths[i].empty())
                continue;
            try {
                assets.slots[i] = readWav(next.samplePaths[i]);
            } catch (const std::exception&) {
                missing += " " + std::to_string(i + 1);
            }
        }
        replaceAssets([&] {
            bank = std::move(assets);
            state = std::move(next);
            state.apply(engine.params);
            for (size_t i = 0; i < state.cc.size(); ++i)
                host.midiControls.cc[i].store(state.cc[i]);
        });
        return missing.empty() ? "Preset restored."
                               : "Missing samples in slots" + missing + ". Factory sounds substituted.";
    }
    void importSample(size_t slot, const std::filesystem::path& path) {
        validateSlot(slot);
        auto sample = readWav(path);
        replaceAssets([&] {
            bank.slots[slot] = std::move(sample);
            state.samplePaths[slot] = path.string();
        });
        persist();
    }
    SampleInfo sampleInfo(size_t slot) const {
        validateSlot(slot);
        const auto& sample = bank.slots[slot];
        return {sample.frames.size() / sample.rate, sample.frames.size()};
    }
    void editSample(size_t slot, SampleEdit edit) {
        validateSlot(slot);
        const auto& original = bank.slots[slot];
        const double duration = original.frames.size() / original.rate;
        if (!std::isfinite(edit.begin) || !std::isfinite(edit.end) || edit.begin < 0 ||
            edit.end > duration + .000001 || edit.end <= edit.begin || edit.end - edit.begin < .001)
            throw std::runtime_error("Invalid sample trim");
        Sample edited;
        edited.rate = original.rate;
        const auto first = static_cast<size_t>(edit.begin * original.rate);
        const auto last =
            std::min(original.frames.size(), static_cast<size_t>(std::round(edit.end * original.rate)));
        edited.frames.assign(original.frames.begin() + static_cast<std::ptrdiff_t>(first),
                             original.frames.begin() + static_cast<std::ptrdiff_t>(last));
        if (edit.reverse)
            std::reverse(edited.frames.begin(), edited.frames.end());
        if (edit.normalize) {
            float peak = 0;
            for (auto frame : edited.frames)
                peak = std::max({peak, std::abs(frame.l), std::abs(frame.r)});
            if (peak > 1.e-8f)
                for (auto& frame : edited.frames)
                    frame = frame * (.95f / peak);
        }
        const auto folder = sessionPath.parent_path() / "Samples";
        std::filesystem::create_directories(folder);
        const auto stamp = std::chrono::steady_clock::now().time_since_epoch().count();
        const auto path = folder / ("slot-" + std::to_string(slot) + "-" + std::to_string(stamp) + ".wav");
        writeWav(path, edited);
        replaceAssets([&] {
            bank.slots[slot] = std::move(edited);
            state.samplePaths[slot] = path.string();
        });
        persist();
    }

  private:
    // Assets must outlive Host and Engine processing. The destructor stops Host
    // before these members are destroyed.
    SampleBank bank;
    State state;
    std::filesystem::path sessionPath;
    AudioConfiguration route;

    static void validateSlot(size_t slot) {
        if (slot >= 16)
            throw std::out_of_range("Invalid sample slot");
    }
    template <class Replace> void replaceAssets(Replace replace) {
        const bool restart = host.running();
        host.stop();
        replace();
        if (restart)
            start(route);
    }
};
} // namespace rmx
