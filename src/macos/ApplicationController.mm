#include "ApplicationController.h"

ApplicationController::ApplicationController(std::filesystem::path path)
    : session(std::move(path)),
      queue(dispatch_queue_create("nz.axelmckenna.rmx.session", DISPATCH_QUEUE_SERIAL)) {}

void ApplicationController::perform(std::function<std::string()> work, Completion done) {
    working.fetch_add(1);
    auto owner = shared_from_this();
    dispatch_async(queue, ^{
      Result result{true, {}};
      try {
          result.message = work();
      } catch (const std::exception& error) {
          result = {false, error.what()};
      }
      dispatch_async(dispatch_get_main_queue(), ^{
        owner->working.fetch_sub(1);
        if (done)
            done(result);
      });
    });
}
void ApplicationController::start(rmx::AudioConfiguration configuration, Completion done) {
    perform(
        [this, configuration] {
            session.start(configuration);
            return "Audio running.";
        },
        std::move(done));
}
void ApplicationController::stop(Completion done) {
    perform(
        [this] {
            session.stop();
            return "Audio stopped.";
        },
        std::move(done));
}
void ApplicationController::restore(Completion done) {
    perform([this] { return session.restoreSession(); }, std::move(done));
}
void ApplicationController::persist(Completion done) {
    perform(
        [this] {
            session.persist();
            return std::string{};
        },
        std::move(done));
}
void ApplicationController::save(std::filesystem::path path, Completion done) {
    perform(
        [this, path] {
            session.save(path);
            return "Preset saved with sample references and MIDI mappings.";
        },
        std::move(done));
}
void ApplicationController::load(std::filesystem::path path, Completion done) {
    perform([this, path] { return session.load(path); }, std::move(done));
}
void ApplicationController::importSample(size_t slot, std::filesystem::path path, Completion done) {
    perform(
        [this, slot, path] {
            session.importSample(slot, path);
            return "Sample imported.";
        },
        std::move(done));
}
void ApplicationController::editSample(size_t slot, rmx::SampleEdit edit, Completion done) {
    perform(
        [this, slot, edit] {
            session.editSample(slot, edit);
            return "Edited sample saved and installed.";
        },
        std::move(done));
}
rmx::SampleInfo ApplicationController::sampleInfo(size_t slot) {
    if (slot >= 16)
        throw std::out_of_range("Invalid sample slot");
    __block rmx::SampleInfo result;
    dispatch_sync(queue, ^{
      result = session.sampleInfo(slot);
    });
    return result;
}
void ApplicationController::shutdown(Completion done) {
    perform(
        [this] {
            session.stop();
            session.persist();
            return std::string{};
        },
        std::move(done));
}
void ApplicationController::selectMidiSource(MIDIEndpointRef source) {
    perform(
        [this, source] {
            session.host.selectMidiSource(source);
            return std::string{};
        },
        {});
}
void ApplicationController::change(rmx::Param p, float value) {
    session.engine.params.set(p, value);
    const auto& info = rmx::parameters[static_cast<size_t>(p)];
    session.host.sendFeedback(p, (session.engine.params.get(p) - info.min) / (info.max - info.min));
}
void ApplicationController::sendEvent(rmx::Event event, double seconds) {
    if (session.host.running()) {
        session.engine.enqueue(event);
        return;
    }
    if (event.type == rmx::EventType::Tap) {
        if (lastTap > 0 && seconds > lastTap) {
            const double bpm = 60 / (seconds - lastTap);
            if (bpm >= 40 && bpm <= 240) {
                change(rmx::Param::Tempo, static_cast<float>(bpm));
                change(rmx::Param::AutoTempo, 0);
            }
        }
        lastTap = seconds;
    } else if (event.type == rmx::EventType::Panic) {
        for (auto p : {rmx::Param::SceneOn, rmx::Param::Low, rmx::Param::Mid, rmx::Param::High,
                       rmx::Param::ReleaseAmount, rmx::Param::XHold, rmx::Param::Overdub})
            change(p, 0);
    } else
        session.engine.enqueue(event);
}
