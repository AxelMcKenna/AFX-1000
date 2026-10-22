#include "LinkSession.h"
#include <cmath>
#ifndef RMX_ENABLE_LINK
#define RMX_ENABLE_LINK 0
#endif
#if RMX_ENABLE_LINK
#include <ableton/Link.hpp>
#include <chrono>
struct LinkSession::Impl { ableton::Link session{120}; };
#else
struct LinkSession::Impl {};
#endif
LinkSession::LinkSession()
#if RMX_ENABLE_LINK
    :impl(std::make_unique<Impl>())
#endif
{}
LinkSession::~LinkSession()=default;
bool LinkSession::available() noexcept {
#if RMX_ENABLE_LINK
    return true;
#else
    return false;
#endif
}
void LinkSession::enable(bool on) {
#if RMX_ENABLE_LINK
    // RMX is an audio effect, so it follows tempo/phase without transporting
    // its audio stream or controlling other applications' play buttons.
    impl->session.enableStartStopSync(false);
    impl->session.enable(on);
#else
    (void)on;
#endif
}
bool LinkSession::enabled() const noexcept {
#if RMX_ENABLE_LINK
    return impl->session.isEnabled();
#else
    return false;
#endif
}
unsigned LinkSession::peers() const noexcept {
#if RMX_ENABLE_LINK
    return static_cast<unsigned>(impl->session.numPeers());
#else
    return 0;
#endif
}
bool LinkSession::capture(int64_t hostMicros,rmx::Transport& result) noexcept {
#if RMX_ENABLE_LINK
    if(!impl->session.isEnabled()||impl->session.numPeers()==0) return false;
    const auto state=impl->session.captureAudioSessionState();
    const double bpm=state.tempo(),beat=state.beatAtTime(std::chrono::microseconds(hostMicros),4.);
    if(!std::isfinite(bpm)||bpm<40||bpm>240||!std::isfinite(beat)) return false;
    result.bpm=bpm; result.beat=beat; result.synced=true; result.playing=true;
    return true;
#else
    (void)hostMicros;(void)result;return false;
#endif
}
