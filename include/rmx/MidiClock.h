#pragma once
#include <array>
#include <algorithm>
#include <cmath>
#include <cstdint>

namespace rmx {
// Audio-thread MIDI timing receiver. Timestamp units are monotonic seconds.
// Tempo is measured across >=6 pulses instead of averaging instantaneous BPM,
// so ordinary timestamp jitter and groups with identical timestamps are safe.
class MidiClock {
public:
    struct Position { double bpm{120},beat{}; bool synced{},playing{true}; };
    void reset() noexcept { anchors={};head=0;size=0;totalTicks=0;nextPulse=0;tempo=120;lastTime=-1;lastBeat=0;stoppedBeat=0;running=false;seenTransport=false;validTempo=false; }
    void receive(uint8_t status,uint8_t a,uint8_t b,double time) noexcept {
        if(!std::isfinite(time)||time<0) return;
        if(status==0xfa) { running=true;seenTransport=true;nextPulse=0;lastBeat=0;lastTime=-1;anchors={};head=0;size=0;validTempo=false; }
        else if(status==0xfb) { running=true;seenTransport=true; }
        else if(status==0xfc) { stoppedBeat=position(time).beat;running=false;seenTransport=true; }
        else if(status==0xf2) { nextPulse=static_cast<uint64_t>((a&127)|((b&127)<<7))*6;lastBeat=nextPulse/24.;stoppedBeat=lastBeat; }
        else if(status==0xf8) {
            if(lastTime>=0&&time<lastTime) return;
            ++totalTicks;
            // Equal timestamps are legal for packets containing several clocks.
            // Count all pulses but only create one anchor per distinct timestamp.
            if(size==0||time>anchors[(head+anchors.size()-1)%anchors.size()].time) {
                for(size_t i=0;i<size;++i) {
                    const auto& anchor=anchors[(head+anchors.size()-1-i)%anchors.size()];
                    const auto ticks=totalTicks-anchor.ticks;const double elapsed=time-anchor.time;
                    if(ticks>=6&&elapsed>=.03&&elapsed<=.6) {
                        const double measured=60*ticks/(24*elapsed);
                        if(measured>=40&&measured<=240) { tempo=validTempo?tempo+(measured-tempo)*.3:measured;validTempo=true; }
                        break;
                    }
                }
                anchors[head]={time,totalTicks};head=(head+1)%anchors.size();size=std::min(size+1,anchors.size());
            }
            lastTime=time;
            if(running) { lastBeat=nextPulse/24.;++nextPulse; }
        }
    }
    Position position(double time) const noexcept {
        Position out;out.bpm=tempo;out.playing=running;
        // A plugin may consume all timestamped clocks in a block before
        // asking for its first sample. Project backwards from the last pulse
        // as well as forwards, rather than pinning the grid to a future tick.
        const double elapsed=lastTime>=0?std::clamp(time-lastTime,-.5,.5):0;
        out.beat=running?std::max(0.,lastBeat+elapsed*tempo/60):stoppedBeat;
        // Explicit MIDI Stop holds the sequencer stopped until Start/Continue
        // or source reset. Audio still passes through the effects as usual.
        // Phase is authoritative from the first pulse after Start, even while
        // the multi-pulse tempo estimate is still acquiring.
        out.synced=seenTransport&&(!running||(lastTime>=0&&std::abs(time-lastTime)<.5));
        return out;
    }
private:
    struct Anchor { double time{};uint64_t ticks{}; };
    std::array<Anchor,32> anchors{};
    size_t head{},size{};
    uint64_t totalTicks{},nextPulse{};
    double tempo{120},lastTime{-1},lastBeat{},stoppedBeat{};
    bool running{},seenTransport{},validTempo{};
};

// Per-port parser. System real-time bytes may occur between any two data
// bytes and must leave running status and Song Position Pointer intact.
class MidiStreamParser {
public:
    void reset() noexcept { status=first=needed=received=0; }
    template<class Send> void byte(uint8_t value,Send&& send) noexcept {
        if(value>=0xf8) { send(value,uint8_t{0},uint8_t{0});return; }
        if(value&0x80) {
            received=0;status=value;
            if(value<0xf0) needed=((value&0xf0)==0xc0||(value&0xf0)==0xd0)?1:2;
            else if(value==0xf2) needed=2;
            else if(value==0xf1||value==0xf3) needed=1;
            else { status=0;needed=0; }
            return;
        }
        if(!status) return;
        if(received++==0) first=value;
        if(received==needed) {
            send(status,first,needed==2?value:uint8_t{0});received=0;
            if(status>=0xf0) status=0;
        }
    }
private:
    uint8_t status{},first{},needed{},received{};
};
}
