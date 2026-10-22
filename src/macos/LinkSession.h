#pragma once
#include "rmx/Engine.h"
#include <cstdint>
#include <memory>

// The optional Ableton SDK is confined to this adapter. Default builds contain
// no Link code and never discover peers or open network sockets.
class LinkSession {
public:
    LinkSession();
    ~LinkSession();
    LinkSession(const LinkSession&)=delete;
    LinkSession& operator=(const LinkSession&)=delete;
    static bool available() noexcept;
    void enable(bool enabled); // Main/control thread only.
    bool enabled() const noexcept;
    unsigned peers() const noexcept;
    // Audio thread only. hostMicros must share the macOS mach_absolute_time
    // epoch and represent audible output time, including device latency.
    bool capture(int64_t hostMicros,rmx::Transport& result) noexcept;
private:
    struct Impl;
    std::unique_ptr<Impl> impl;
};
