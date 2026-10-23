#pragma once
#include "AudioHost.h"
#include "rmx/app/ApplicationSession.h"
#include <dispatch/dispatch.h>
#include <functional>
#include <memory>

// Public commands are issued on the main thread. Workflow bodies and all
// audio start/stop/asset mutations run on the private serial control queue.
class ApplicationController : public std::enable_shared_from_this<ApplicationController> {
  public:
    struct Result {
        bool ok;
        std::string message;
    };
    using Completion = std::function<void(Result)>;
    explicit ApplicationController(std::filesystem::path path);
    rmx::Engine& engine() {
        return session.engine;
    }
    AudioHost& audio() {
        return session.host;
    }
    bool busy() const {
        return working.load();
    }
    void start(rmx::AudioConfiguration, Completion);
    void stop(Completion);
    void restore(Completion);
    void persist(Completion = {});
    void save(std::filesystem::path, Completion);
    void load(std::filesystem::path, Completion);
    void importSample(size_t, std::filesystem::path, Completion);
    void editSample(size_t, rmx::SampleEdit, Completion);
    rmx::SampleInfo sampleInfo(size_t);
    void shutdown(Completion);
    void selectMidiSource(MIDIEndpointRef);
    void change(rmx::Param, float);
    void sendEvent(rmx::Event, double seconds);

  private:
    rmx::ApplicationSession<AudioHost> session;
    dispatch_queue_t queue;
    std::atomic<size_t> working{};
    double lastTap{}; // Main-thread input handling while audio is stopped.
    void perform(std::function<std::string()> work, Completion);
};
