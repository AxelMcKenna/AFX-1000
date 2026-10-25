#include "BoardIO.h"
#include "BootCard.h"
#include "Calibration.h"
#include "ConnectionMode.h"
#include "RelayFeedback.h"
#include "daisy_seed.h"
#include "rmx/controls/HardwareControls.h"
#if RMX_EXTERNAL_CONVERTER
#include "ConverterPower.h"
#include "Es9292.h"
#include "ExternalAudio.h"
#include "InputQualification.h"
#endif
#include <atomic>

void initializeAudioMemory();
size_t audioMemoryUsed();
namespace {
daisy::DaisySeed hw;
rmx::Engine engine;
rmx::SampleBank bank;
rmx::hardware::Controls controls(engine);
rmx::hardware::Debouncer debounce;
rmx::embedded::BoardIO io;
rmx::embedded::Calibration calibration(hw.qspi);
rmx::embedded::ConnectionMode connection;
rmx::embedded::RelayFeedback relayFeedback;
rmx::embedded::RearmDelay rearmDelay;
std::atomic<bool> fault{}, requestProcessing{};
std::atomic<uint32_t> blocks{}, maxCallbackUs{}, deadlineMisses{}, lastHealthyControls{};
std::atomic<uint32_t> audioHeapBytes{};
rmx::embedded::CardReport cardReport;
#if RMX_EXTERNAL_CONVERTER
rmx::embedded::ExternalAudio externalAudio;
rmx::embedded::ConverterSession<rmx::embedded::BoardIO> converter(io);
rmx::embedded::InputQualification inputQualification;
#endif

void audioFault() {
    fault.store(true, std::memory_order_relaxed);
    requestProcessing.store(false, std::memory_order_relaxed);
    io.relayPermit(false);
#if RMX_EXTERNAL_CONVERTER
    externalAudio.audible(false);
    externalAudio.inputQualified(false);
#endif
}

void audio(daisy::AudioHandle::InputBuffer input, daisy::AudioHandle::OutputBuffer output, size_t frames) {
    const uint32_t start = daisy::System::GetUs();
    engine.process(input[0], input[1], output[0], output[1], static_cast<uint32_t>(frames));
    for (size_t i = 0; i < frames; ++i) {
        if (!std::isfinite(output[0][i]) || !std::isfinite(output[1][i])) {
            output[0][i] = output[1][i] = 0;
            fault.store(true, std::memory_order_relaxed);
        }
        output[0][i] = std::clamp(output[0][i], -1.f, 1.f);
        output[1][i] = std::clamp(output[1][i], -1.f, 1.f);
    }
    const uint32_t elapsed = daisy::System::GetUs() - start;
    if (elapsed > maxCallbackUs.load(std::memory_order_relaxed))
        maxCallbackUs.store(elapsed, std::memory_order_relaxed);
    if (elapsed > 2400) {
        deadlineMisses.fetch_add(1, std::memory_order_relaxed);
        fault.store(true, std::memory_order_relaxed);
    }
    const bool healthy = !fault.load(std::memory_order_relaxed);
    if (!healthy) {
        std::fill_n(output[0], frames, 0.f);
        std::fill_n(output[1], frames, 0.f);
    }
    const bool controlsFresh =
        static_cast<uint32_t>(daisy::System::GetNow() -
                              lastHealthyControls.load(std::memory_order_relaxed)) <= 20;
    // Callback owns the running relay permit. A stalled foreground loop cannot
    // keep it enabled with a stale request. Physical bypass also gates it in HW.
    io.relayPermit(healthy && controlsFresh && requestProcessing.load(std::memory_order_relaxed));
    if (healthy)
        io.audioHeartbeat();
    blocks.fetch_add(1, std::memory_order_relaxed);
}
void displayWord(std::array<uint16_t, 96>& led, std::array<uint8_t, 3> word) {
    for (size_t digit = 0; digit < 3; ++digit)
        for (size_t bit = 0; bit < 8; ++bit)
            led[69 + 8 * digit + bit] = word[digit] & (1 << bit) ? 4095 : 0;
}
bool startAudio() {
#if RMX_EXTERNAL_CONVERTER
    return externalAudio.start(audio, audioFault);
#else
    hw.StartAudio(audio);
    return true;
#endif
}
bool stopAudio() {
#if RMX_EXTERNAL_CONVERTER
    return externalAudio.stop();
#else
    hw.StopAudio();
    return true;
#endif
}
[[noreturn]] void initializationFailed() {
    audioFault();
    io.disableConverter();
    for (;;) {
        hw.SetLed(true);
        daisy::System::Delay(100);
        hw.SetLed(false);
        daisy::System::Delay(100);
    }
}
} // namespace

int main() {
    hw.Init(true);
    const bool initialized = io.initialize();
    if (!initialized)
        initializationFailed();
    initializeAudioMemory();
    bank = rmx::makeFactoryBank(48000);
    engine.setBank(&bank);
    engine.prepare(48000, 128);
    // Filesystem access ends before audio, heartbeat, converter startup or permit.
    cardReport = rmx::embedded::loadBootCard(bank, engine.params);
    engine.params.set(rmx::Param::WetOnly, 0.f);
    audioHeapBytes.store(static_cast<uint32_t>(audioMemoryUsed()), std::memory_order_relaxed);
#if RMX_EXTERNAL_CONVERTER
    rmx::embedded::ConverterPower<rmx::embedded::BoardIO> converterPower(io);
    for (;;) {
        const auto power = converterPower.poll(daisy::System::GetNow());
        if (power == decltype(converterPower)::State::Fault)
            initializationFailed();
        if (power == decltype(converterPower)::State::Ready)
            break;
        // Audio/heartbeat/permit have not started. E11 stays in dry bypass.
        daisy::System::Delay(1);
    }
    if (!converter.prepare(daisy::System::GetNow()) || !externalAudio.initialize(hw))
        initializationFailed();
#else
    hw.SetAudioSampleRate(daisy::SaiHandle::Config::SampleRate::SAI_48KHZ);
    hw.SetAudioBlockSize(128);
#endif
    daisy::AdcChannelConfig adc[10];
    for (size_t i = 0; i < 10; ++i)
        adc[i].InitSingle(daisy::DaisySeed::GetPin(15 + i));
    hw.adc.Init(adc, 10);
    hw.adc.Start();
    daisy::System::Delay(20);
    std::array<float, 10> filtered{};
    for (size_t i = 0; i < 10; ++i) {
        filtered[i] = hw.adc.GetFloat(i);
        controls.knob(static_cast<rmx::hardware::Knob>(i), filtered[i]);
    }
    uint32_t keys;
    if (!io.buttons(keys) || !io.pollRearStatus())
        initializationFailed();
    debounce.begin(keys);
    controls.initializeButtons(keys & 0x1fffffff);
    calibration.load();
    if (!startAudio())
        initializationFailed();
    uint32_t lastPoll = 0, lastTouch = 0, lastLed = 0, chordAt = 0;
    bool chordDown = false, chordFired = false, calibrating = false, haveHome = false, touchHealthy = false;
    uint16_t homeRaw = 0;
#if RMX_EXTERNAL_CONVERTER
    uint32_t lastConverterPoll = 0;
#endif
    for (;;) {
        const uint32_t now = daisy::System::GetNow();
        if (static_cast<uint32_t>(now - lastPoll) < 1)
            continue;
        const bool loopDelayed = static_cast<uint32_t>(now - lastPoll) > 20;
        lastPoll = now;
        const bool rearHealthy = io.pollRearStatus();
#if RMX_EXTERNAL_CONVERTER
        if (!rearHealthy)
            audioFault();
        if (externalAudio.hardwareError())
            audioFault();
        if (!fault.load(std::memory_order_relaxed) && static_cast<uint32_t>(now - lastConverterPoll) >= 4) {
            lastConverterPoll = now;
            if (converter.poll(now, blocks.load(std::memory_order_relaxed), rearHealthy,
                               io.analogQualified()) ==
                rmx::embedded::ConverterSession<rmx::embedded::BoardIO>::State::Fault)
                audioFault();
        }
        // An observed hardware qualifier loss also revokes permit between codec
        // polls. E09's physical ANALOG_OK path does not depend on this polling.
        if (converter.ready() && !io.analogQualified())
            audioFault();
        if (fault.load(std::memory_order_relaxed))
            io.disableConverter();
#endif
        const auto gain = connection.update(io.sendReturn(), now);
        if (!gain.ready) {
            requestProcessing.store(false, std::memory_order_relaxed);
            io.relayPermit(false);
#if RMX_EXTERNAL_CONVERTER
            externalAudio.inputQualified(false);
            externalAudio.audible(false);
#endif
        }
        io.connectionGain(gain.driveSendReturn);
#if RMX_EXTERNAL_CONVERTER
        auto inputState = inputQualification.update(converter.ready() && gain.ready &&
                                                        !fault.load(std::memory_order_relaxed),
                                                    io.inputQualified(), rearHealthy, now);
        bool inputReady = inputState.ready;
        if (!inputReady) {
            requestProcessing.store(false, std::memory_order_relaxed);
            io.relayPermit(false);
            externalAudio.inputQualified(false);
            externalAudio.audible(false);
        }
        if (inputState.fault)
            audioFault();
#endif
        bool healthy = io.buttons(keys) && rearHealthy && !loopDelayed;
        uint16_t angle = 0;
        const bool angleValid = io.releaseAngle(angle);
        healthy = healthy && angleValid;
        if (healthy) {
            const uint32_t edges = debounce.update(keys, now), stable = debounce.state();
            for (size_t i = 0; i < 29; ++i)
                if (edges & (uint32_t(1) << i))
                    controls.button(static_cast<rmx::hardware::Button>(i), bool(stable & (uint32_t(1) << i)),
                                    now);
            controls.settings(stable & (uint32_t(1) << 29));
            healthy = controls.releaseSelection(stable & (uint32_t(1) << 30), stable & (uint32_t(1) << 31));
            const bool chord =
                io.manualBypass() && (stable & (uint32_t(1) << 2)) && (stable & (uint32_t(1) << 11));
            if (chord && !chordDown) {
                chordAt = now;
                chordFired = false;
            }
            if (chord && !chordFired && static_cast<uint32_t>(now - chordAt) >= 2000) {
                chordFired = true;
                calibrating = true;
                if (!haveHome) {
                    homeRaw = angle;
                    haveHome = true;
                } else {
                    requestProcessing.store(false, std::memory_order_relaxed);
                    io.relayPermit(false);
                    daisy::System::Delay(10);
                    if (!stopAudio())
                        audioFault();
                    if (calibration.save(homeRaw, angle)) {
                        haveHome = false;
                        calibrating = false;
                        controls.release(0);
                        engine.enqueue({rmx::EventType::Panic});
                        engine.params.set(rmx::Param::Bank, 0);
                    }
                    blocks.store(0, std::memory_order_relaxed);
#if RMX_EXTERNAL_CONVERTER
                    converter.restartSilent(daisy::System::GetNow());
                    inputQualification.update(false, false, rearHealthy, daisy::System::GetNow());
                    inputReady = false;
#endif
                    if (!startAudio())
                        audioFault();
                }
            }
            chordDown = chord;
            for (size_t i = 0; i < 10; ++i) {
                filtered[i] += .25f * (hw.adc.GetFloat(i) - filtered[i]);
                controls.knob(static_cast<rmx::hardware::Knob>(i), filtered[i]);
            }
            controls.release(calibration.position(angle), calibration.ready());
        } else {
            controls.release(0, false);
        }
        if (static_cast<uint32_t>(now - lastTouch) >= 4) {
            lastTouch = now;
            rmx::embedded::Touch touch;
            touchHealthy = io.touch(touch);
            controls.touch(touchHealthy ? touch.position : 0, touchHealthy && touch.active);
        }
        healthy = healthy && touchHealthy && gain.ready &&
                  (!calibration.ready() || calibrating || calibration.plausible(angle));
#if RMX_EXTERNAL_CONVERTER
        healthy = healthy && converter.ready() && io.analogQualified();
        externalAudio.inputQualified(inputReady && converter.ready() &&
                                     !fault.load(std::memory_order_relaxed));
        externalAudio.audible(healthy && inputReady && !fault.load(std::memory_order_relaxed));
#endif
        controls.tick(now);
        const bool bypassRequested = io.manualBypass();
        engine.params.set(rmx::Param::Bypass, bypassRequested ? 1.f : 0.f);
        if (healthy)
            lastHealthyControls.store(now, std::memory_order_relaxed);
        const bool eligible = healthy && calibration.ready() && !calibrating && !bypassRequested
#if RMX_EXTERNAL_CONVERTER
                              && inputReady
#endif
                              && blocks.load(std::memory_order_relaxed) > 128 &&
                              !fault.load(std::memory_order_relaxed);
        const bool desired = rearmDelay.update(eligible, now);
        const auto relay = relayFeedback.update(desired, io.hardwareArmed(), now);
        if (relay.fault)
            fault.store(true, std::memory_order_relaxed);
        requestProcessing.store(relay.allowPermit && !fault.load(std::memory_order_relaxed),
                                std::memory_order_relaxed);
        if (!relay.allowPermit)
            io.relayPermit(false);
        if (static_cast<uint32_t>(now - lastLed) >= 33) {
            lastLed = now;
            auto led = controls.feedback(now);
#if RMX_EXTERNAL_CONVERTER
            if (!inputReady && !bypassRequested)
                displayWord(led, {0x06, 0x54, 0});
#endif
            if (!calibration.ready() || calibrating)
                displayWord(led, haveHome ? std::array<uint8_t, 3>{0x79, 0x54, 0x5e}
                                          : std::array<uint8_t, 3>{0x39, 0x77, 0x38});
            if (!healthy || fault.load(std::memory_order_relaxed)) {
                displayWord(led, {0x79, 0x50, 0x50});
                led[93] = 4095;
                led[94] = led[95] = 0;
            }
            if (!io.feedback(led))
                fault.store(true, std::memory_order_relaxed);
            hw.SetLed(healthy && !fault.load(std::memory_order_relaxed));
        }
    }
}
