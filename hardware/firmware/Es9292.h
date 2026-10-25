#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

namespace rmx::embedded {
// ES9292PRO v0.1, pp.105-169. Bus uses seven-bit address 0x18 and
// single-register transactions. Paired registers are latched LSB -> MSB.
template <class Bus> class Es9292 {
  public:
    static constexpr uint8_t address = 0x18;
    struct Setting {
        uint8_t reg, count;
        uint16_t mask, value;
    };
    inline static constexpr auto settings = std::to_array<Setting>({
        {116, 1, 0x33, 0x33}, // Mute DAC and direct monitor during setup.
        {1, 1, 0x17, 0x02},   // Fixed 128fs division; block automatic 64fs.
        {2, 1, 0xff, 0x11},   // PCM encoder / decoder only.
        {3, 1, 0xcf, 0},
        {4, 1, 0x8f, 0}, // Explicit PCM output/input.
        {5, 1, 0x7f, 3},
        {6, 1, 0x10, 0}, // MCLK/4 = 128fs, 24.576MHz backend.
        {7, 1, 0xff, 7},
        {8, 1, 0x0f, 0x0d}, // BCLK=MCLK/8; clock monitors on.
        {10, 1, 0x5f, 1},
        {11, 1, 0x7f, 0}, // Stereo, 32-bit I2S, falling WS.
        {12, 2, 0x1f1f, 0x0100},
        {14, 2, 0x1f1f, 0x0100}, // L/R slot 0/1.
        {16, 1, 0x9f, 0},
        {17, 1, 0x9f, 0}, // No daisy chain / slot adjustment.
        {61, 1, 0xff, 0},
        {62, 1, 0xff, 0x62}, // GPIO3 clock; GPIO4 ramp done.
        {63, 2, 0xffff, 0},
        {65, 1, 0x0f, 0},
        {66, 2, 0x01ff, 0},
        {68, 2, 0x01ff, 0}, // Inputs/outputs initially off.
        {70, 2, 0x01ff, 0},
        {72, 2, 0x01ff, 0},
        {74, 2, 0x01ff, 0},
        {77, 1, 0x7f, 4}, // AND both ramp flags; OR override disabled.
        {81, 1, 3, 0},
        {82, 1, 0xff, 0},        // No inversion, minimum-phase ADC.
        {83, 2, 0x3c00, 0x3000}, // ADC DC blockers, built-in FIR; reserved LSB kept.
        {89, 2, 0xffff, 0},
        {91, 1, 0x77, 0},
        {92, 1, 3, 0},
        {105, 1, 0xff, 0},
        {110, 2, 0xffff, 0x0202}, // DAC filter, unity volume.
        {112, 2, 0xffff, 0xffff},
        {114, 1, 0x77, 0},
        {115, 1, 0xff, 0},
        {117, 1, 0x6f, 3}, // Retain DC bias while muted; normal soft start.
        {118, 2, 0xffff, 0},
        {120, 1, 3, 0}, // No DC trim; disable automute.
        {136, 1, 0x7c, 0},
        {137, 1, 0x0f, 0}, // Direct ACLK1; PLL unused.
        {147, 1, 0xef, 0},
        {148, 1, 0x33, 0x33}, // No internal ASP processing.
        {0, 1, 0xbf, 0x2f},   // Enable stereo ADC/DAC, ACLK1; no soft reset.
        {9, 1, 0xbf, 0x25},   // PCM master; default ESS I2S clock phase.
    });

    explicit Es9292(Bus& bus) : bus_(bus) {}
    bool prepare() {
        configured_ = active_ = false;
        audit_ = 0;
        uint8_t id = 0;
        if (!bus_.codecRead(225, id) || id != 0xaf)
            return false;
        // Suppress flags, mute and stop paths/master before changing format.
        for (auto s : std::to_array<Setting>(
                 {{68, 2, 0x01ff, 0}, {116, 1, 0x33, 0x33}, {0, 1, 0xbf, 0x20}, {9, 1, 0xbf, 0x24}}))
            if (!apply(s))
                return false;
        for (auto s : settings)
            if (!apply(s))
                return false;
        configured_ = true;
        return true;
    }
    bool activateSilentStream() {
        if (!configured_ || active_)
            return false;
        // Caller has started zero-filled DMA. Unmute before enabling the flags
        // that start the external settling timer. Keep direct monitor muted.
        if (!apply({116, 1, 0x33, 0x30}) || !apply({68, 2, 0x01ff, 0x000c}))
            return false;
        active_ = true;
        return true;
    }
    bool auditNext() {
        if (!configured_)
            return false;
        auto s = settings[audit_];
        audit_ = (audit_ + 1) % settings.size();
        if (active_ && s.reg == 116)
            s.value = 0x30;
        if (active_ && s.reg == 68)
            s.value = 0x0c;
        uint16_t value = 0;
        return read(s, value) && (value & s.mask) == s.value;
    }
    bool status(bool& clocks, bool& ramped) {
        uint8_t enc = 0, dec = 0, clock = 0, ramp = 0;
        if (!bus_.codecRead(218, enc) || !bus_.codecRead(219, dec) || !bus_.codecRead(221, clock) ||
            !bus_.codecRead(241, ramp))
            return false;
        clocks = (enc & 0x0f) == 1 && (dec & 0x71) == 1 && (clock & 0xe0) == 0x80;
        // Distinguish fully ramped UP from 'not currently ramping' GPIO flag.
        ramped = ramp == 0x30;
        return true;
    }

  private:
    Bus& bus_;
    bool configured_ = false, active_ = false;
    size_t audit_ = 0;
    bool read(Setting s, uint16_t& value) {
        value = 0;
        for (uint8_t i = 0; i < s.count; ++i) {
            uint8_t byte = 0;
            if (!bus_.codecRead(s.reg + i, byte))
                return false;
            value |= static_cast<uint16_t>(byte) << (8 * i);
        }
        return true;
    }
    bool apply(Setting s) {
        uint16_t old = 0, actual = 0;
        if (!read(s, old))
            return false;
        const uint16_t value = (old & ~s.mask) | s.value;
        // Always write the complete pair, including an unchanged LSB, so MSB
        // latching cannot commit a stale low byte. Check only after both writes.
        for (uint8_t i = 0; i < s.count; ++i)
            if (!bus_.codecWrite(s.reg + i, static_cast<uint8_t>(value >> (8 * i))))
                return false;
        return read(s, actual) && actual == value;
    }
};

// Foreground qualification complements E09's independent hardware interlock.
// Faults latch until reboot; no automatic codec reconfiguration while armed.
template <class Bus> class ConverterSession {
  public:
    enum class State { Unconfigured, Silent, Settling, Ready, Fault };
    static constexpr uint32_t timeoutMs = 8000, minimumSettleMs = 1211, staleAudioMs = 20;
    explicit ConverterSession(Bus& bus) : codec_(bus) {}
    bool prepare(uint32_t now) {
        if (state_ != State::Unconfigured)
            return false;
        if (!codec_.prepare()) {
            state_ = State::Fault;
            return false;
        }
        since_ = lastAudio_ = now;
        state_ = State::Silent;
        return true;
    }
    State poll(uint32_t now, uint32_t blocks, bool statusValid, bool analogOk) {
        if (state_ == State::Fault || state_ == State::Unconfigured)
            return state_;
        if (!statusValid)
            return fail();
        if (state_ != State::Ready && static_cast<uint32_t>(now - since_) >= timeoutMs)
            return fail();
        if (blocks != lastBlocks_) {
            lastBlocks_ = blocks;
            lastAudio_ = now;
        }
        const bool streaming = blocks >= 4 && static_cast<uint32_t>(now - lastAudio_) <= staleAudioMs;
        if (state_ == State::Silent && streaming) {
            if (!activated_ && !codec_.activateSilentStream())
                return fail();
            activated_ = true;
            since_ = now;
            state_ = State::Settling;
        }
        bool clocks = false, ramped = false;
        if (!codec_.status(clocks, ramped) || !codec_.auditNext())
            return fail();
        const bool stable = streaming && clocks && ramped && state_ != State::Silent;
        if (!stable)
            quiet_ = false;
        else if (!quiet_) {
            quiet_ = true;
            quietSince_ = now;
        }
        const bool qualified = stable && analogOk;
        if (state_ == State::Ready) {
            if (!qualified)
                return fail();
        } else if (state_ == State::Settling && qualified &&
                   static_cast<uint32_t>(now - quietSince_) >= minimumSettleMs)
            state_ = State::Ready;
        return state_;
    }
    bool ready() const {
        return state_ == State::Ready;
    }
    State state() const {
        return state_;
    }
    void restartSilent(uint32_t now) {
        if (state_ == State::Unconfigured || state_ == State::Fault)
            return;
        // Calibration pauses DMA, not codec clocks or DC bias. Do not rewrite
        // analog registers; require fresh callbacks and another quiet interval.
        since_ = lastAudio_ = now;
        lastBlocks_ = 0;
        quiet_ = false;
        state_ = State::Silent;
    }

  private:
    Es9292<Bus> codec_;
    State state_ = State::Unconfigured;
    bool activated_ = false, quiet_ = false;
    uint32_t since_ = 0, lastAudio_ = 0, lastBlocks_ = 0, quietSince_ = 0;
    State fail() {
        state_ = State::Fault;
        return state_;
    }
};
} // namespace rmx::embedded
