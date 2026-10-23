#include "TestSupport.h"
#include "rmx/app/ApplicationSession.h"
#include "rmx/controls/MidiControls.h"

namespace {
struct FakeHost {
    rmx::Engine& engine;
    rmx::MidiControls midiControls;
    bool active{}, failStart{};
    int starts{}, stops{};
    rmx::AudioConfiguration lastRoute;
    explicit FakeHost(rmx::Engine& engine) : engine(engine) {}
    bool running() const {
        return active;
    }
    void stop() {
        active = false;
        ++stops;
    }
    bool start(uint32_t input, uint32_t output, uint32_t inPair, uint32_t outPair, uint32_t frames,
               std::string& error) {
        lastRoute = {input, output, inPair, outPair, frames, false};
        ++starts;
        if (failStart) {
            error = "Device disconnected";
            return false;
        }
        engine.prepare(48000, frames);
        active = true;
        return true;
    }
    bool startRekordbox(uint32_t output, uint32_t outPair, uint32_t frames, std::string& error) {
        const bool result = start(0, output, 0, outPair, frames, error);
        lastRoute.applicationCapture = true;
        return result;
    }
};
} // namespace
int main() {
    return runTests([] {
        const auto folder =
            std::filesystem::temp_directory_path() /
            ("rmx-session-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
        std::filesystem::create_directories(folder);
        struct Cleanup {
            std::filesystem::path path;
            ~Cleanup() {
                std::filesystem::remove_all(path);
            }
        } cleanup{folder};
        rmx::ApplicationSession<FakeHost> session(folder / "session.rmx");
        require(session.restoreSession().empty(), "Fresh session failed to start without saved state");
        session.engine.params.set(rmx::Param::SceneDepth, .8f);
        session.persist();
        session.start({1, 2, 2, 4, 256, false});
        rmx::Sample sample;
        sample.frames.resize(480);
        for (size_t i = 0; i < sample.frames.size(); ++i)
            sample.frames[i] = {static_cast<float>(i) / 1000, 0};
        const auto wav = folder / "sample.wav";
        rmx::writeWav(wav, sample);
        const int before = session.host.starts;
        session.importSample(3, wav);
        require(session.host.running() && session.host.starts == before + 1 && session.host.stops > 0,
                "Asset replacement did not suspend/resume audio");
        require(session.host.lastRoute.inputPair == 2 && session.host.lastRoute.outputPair == 4 &&
                    session.host.lastRoute.bufferFrames == 256,
                "Asset replacement lost route configuration");
        session.editSample(3, {.001, .006, true, true});
        auto saved = rmx::State::load(folder / "session.rmx");
        auto edited = rmx::readWav(saved.samplePaths[3]);
        require(edited.frames.size() == 240 && std::abs(edited.frames.front().l - .95f) < 1.e-6,
                "Managed sample trim/reverse/normalization failed");
        session.engine.params.set(rmx::Param::SceneDepth, .2f);
        session.load(folder / "session.rmx");
        require(session.engine.params.get(rmx::Param::SceneDepth) == .8f,
                "Preset workflow lost parameter state");
        const int runningStarts = session.host.starts;
        bool rejected = false;
        try {
            session.importSample(3, folder / "missing.wav");
        } catch (const std::exception&) {
            rejected = true;
        }
        require(rejected && session.host.running() && session.host.starts == runningStarts,
                "Invalid input interrupted an active route");
        session.host.failStart = true;
        rejected = false;
        try {
            session.importSample(3, wav);
        } catch (const std::exception&) {
            rejected = true;
        }
        require(rejected && !session.host.running(), "Failed restart left audio marked active");
        session.host.failStart = false;
        session.start({0, 5, 0, 6, 128, true});
        session.importSample(3, wav);
        require(session.host.lastRoute.applicationCapture && session.host.lastRoute.output == 5,
                "Capture route was not restored after sample import");
        session.stop();
        session.persist();
        require(!session.host.running(), "Shutdown retained an active route");
    });
}
