# RMX Lab

A small macOS stereo audio prototype with a three-band isolator and tempo-based echo. It is a standalone application that uses Core Audio through AVAudioEngine; it is not a rekordbox plug-in and does not assume that rekordbox can host Audio Units or VSTs.

## Build and launch

Requirements: macOS 14 or later, Xcode command line tools, and Swift 6.

1. In Terminal, go to this folder and run `./build-app.sh`.
2. Open `RMX Lab.app` from this folder.
3. Allow microphone/audio-input access when macOS asks.
4. Set the intended interface as both the macOS default input and output in **Audio MIDI Setup**. Connect headphones or monitor output before starting.
5. Click **Start Audio**. Start with the echo mix at 0%, all isolator bands at 0 dB, and the monitoring level low.

The app currently uses the macOS default input and output. It reports the input/output channel counts and sample rate after starting. It does not yet offer per-device or multichannel selection.

## Rekordbox and external mixer routing

Pioneer DJ documents a rekordbox **Use FX1 and FX2 as FX SEND/RETURN** option only when compatible DJ equipment is connected and selected as rekordbox's audio device. The published compatible-device list includes DJM-V10, DJM-TOUR1, DJM-A9, DJM-900NXS2, DJM-750MK2, DJM-450, DJM-250MK2, euphonia, and XDJ-XZ (list stated by Pioneer as correct in March 2024). This app does not register with rekordbox or appear as that native effect.

For a mixer/controller with physical FX send and return connections, the generic audio path is:

```text
Mixer FX SEND L/R → audio interface inputs 1/2 → RMX Lab → interface outputs 1/2 → mixer FX RETURN L/R
```

If the DJ hardware exposes suitable send/return channels through its USB audio interface, those channels may serve instead of a separate interface, but the channel mapping is hardware-specific. Do not choose channels by guesswork. Set the relevant interface as macOS's default audio device, start with send level low and the app echo mix at 0%, then route signal and confirm clean dry pass-through before adding echo. Check for feedback, clipping, and a stable return before raising levels. Disable direct monitoring for the send input if it creates a parallel dry signal. Use the mixer return's wet/dry control where available.

Rekordbox's **External** mixer mode is for outputting deck audio to an external mixer; that by itself does not route a third-party app as an insert. Native rekordbox FX SEND/RETURN operation depends on a supported hardware device and its configured send/return routing. The exact mixer/controller model and whether it has physical or USB send/return channels are needed to write a precise setup.

## Audio test plan

1. **Device check:** connect the interface and confirm its stereo input and output are selected as macOS defaults. Start RMX Lab and confirm the status shows the expected sample rate and channel counts.
2. **Dry pass-through:** with all bands at 0 dB and echo mix at 0%, feed a quiet stereo test signal to the interface input. Confirm both sides reach the mixer return without clipping, dropouts, or an audible feedback loop.
3. **Isolator:** lower LOW, MID, and HIGH one at a time. Confirm the expected bass, midrange, and treble reduction. Return each slider to 0 dB after checking.
4. **Echo:** set a low mix (about 10%), moderate feedback (about 25%), and 120 BPM; confirm repeats, then check the 1/4, 1/2, 1-beat, and 2-beat times. Keep feedback below 88%.
5. **Stability:** run a quiet signal for several minutes, then stop and restart the app. If you hear crackles or dropouts, stop the app and increase the interface buffer in Audio MIDI Setup if available.

## Prototype limitations

This first pass uses a tap and scheduled output buffers. That adds buffering latency and the callback does some allocation; this is useful for proving the controls and signal path, but is not suitable for performance or scratching. It is not yet a low-latency production DSP engine. A later performance build should use a native real-time audio callback with preallocated buffers and explicit input/output device and channel selection. There is no BPM detection or rekordbox tempo sync in this version; BPM is set manually.
