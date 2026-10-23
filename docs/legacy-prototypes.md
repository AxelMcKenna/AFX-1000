# Browser prototype

## Run the historical web prototype

The browser version lives in `prototypes/web/` and uses an `AudioWorklet` processor for the stereo isolator and beat echo. It is the quickest version to run and modify. No package install or build step is needed.

1. In Terminal, go to this folder and run `python3 -m http.server 8000`.
2. Open `http://localhost:8000/prototypes/web/` in a recent desktop browser.
3. Allow microphone access, select an audio input if the browser offers it, and click **Start Audio**.
4. Select an output device if the browser supports output selection. Otherwise set the interface as the macOS default output in Audio settings or Audio MIDI Setup.
5. Start with the isolator at 0 dB and echo wet at 0%. Use headphones while checking the send/return path.

The browser reports its base audio latency, but that value excludes some device and routing latency. `AudioWorklet` avoids doing the DSP on the UI thread; it does not guarantee a fixed or performance-grade latency. The web app is still a standalone effect and does not register as a rekordbox plug-in.

The Swift tap/player prototype has been retired. It allocated output buffers and acquired a lock in the audio callback, and scheduled playback added buffering latency. Use the maintained [native macOS app](../README.md#run-it), which shares its preallocated C++ engine with the AU/VST3 adapters. Current routing instructions are in the [routing guide](routing.md).
