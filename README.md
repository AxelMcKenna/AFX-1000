<img src="assets/readme-hero.svg" alt="RMX. Software effects unit." width="100%">

[![Build](https://github.com/AxelMcKenna/RMX-1000-Clone/actions/workflows/build.yml/badge.svg)](https://github.com/AxelMcKenna/RMX-1000-Clone/actions/workflows/build.yml)
![macOS 12+](https://img.shields.io/badge/macOS-12%2B-222222?style=flat-square&logo=apple&logoColor=white)
![Standalone / AU / VST3](https://img.shields.io/badge/Standalone-AU_%2F_VST3-222222?style=flat-square)

A software take on the RMX-1000. Native macOS app, AU and VST3, with an amber/teal panel and a shared C++20 audio engine.

Works with rekordbox through audio capture or an interface. The effects are original implementations; matching the hardware's sound is still a work in progress.

## What's in it

- **Scene FX:** BPF Echo, Echo, Noise, Spiral Up, Reverb Up, HPF Echo, LPF Echo, Crush Echo, Spiral Down and Reverb Down.
- **Isolate FX:** three bands, with Isolator, Cut/Add, Trans/Roll and Gate/Drive modes.
- **X-Pad:** four sample banks, 16 synthesized sounds, WAV import, pitch, rolls, hold and overdub.
- **Release FX:** Back Spin, Echo and Vinyl Brake.

Auto BPM, tap tempo, quantized rolls, MIDI learn, soft takeover and DAW automation are included.

## Run it

Requires macOS 12+, Xcode Command Line Tools and CMake 3.24+. The native app has no external library dependencies.

```sh
git clone git@github.com:AxelMcKenna/RMX-1000-Clone.git
cd RMX-1000-Clone
./build-app.sh
open build/RMX.app
```

**Cmd+,** opens audio setup. Pick an input and output, then start audio.

**Space** bypasses. **Esc** resets the effects. **T** taps tempo. **1-4** trigger the pads. Hold **Shift** while dragging for fine adjustments.

### With rekordbox

On macOS 14.2+, select **rekordbox - direct app capture** as the RMX input and choose your speakers or headphones as the output. Start audio, approve macOS capture access if prompted, then play a track in rekordbox.

The capture route mutes duplicate dry playback while active. Stopping it restores normal rekordbox playback. The AU/VST3 versions are for plugin hosts; rekordbox integration uses audio routing.

For an FLX4 or FLX6 with an audio interface:

```text
FLX master RCA -> Interface inputs -> RMX -> Interface outputs -> Speakers
rekordbox cue  -> FLX headphones
```

Physical FLX routing and cue separation still need testing. BlackHole and mixer send/return setups are covered in the [routing guide](docs/routing.md).

## Build

<details>
<summary>AU, VST3 and JUCE standalone</summary>

```sh
cmake -S . -B build-plugins \
  -DCMAKE_BUILD_TYPE=Release \
  -DRMX_BUILD_PLUGINS=ON
cmake --build build-plugins --parallel 4
```

Fetches JUCE 8.0.6. Use `-DRMX_JUCE_PATH=/path/to/JUCE` for a local checkout. Outputs are in `build-plugins/RMXPlugin_artefacts/Release/`.

For a universal Mac build, use a fresh build directory and add `'-DCMAKE_OSX_ARCHITECTURES=arm64;x86_64'`. Distribution signing and notarization need your Apple credentials. The native build script signs ad hoc for local use.

JUCE's license applies to distribution of the plugin builds.

</details>

<details>
<summary>Core, checks and offline rendering</summary>

The core builds on macOS and Linux, independently of the UI.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 4
ctest --test-dir build --output-on-failure
./build/rmx_benchmark
./build/rmx_render input.wav output.wav "assets/presets/Spiral Build.rmx"
```

The renderer's preset argument is optional. Benchmarks measure DSP time, not physical audio latency.

</details>

## Development checks

The DSP is composed of sampler, sequencer, isolator, scene and release components. Platform adapters share parameter definitions and MIDI/control rules. JUCE parameters directly access the engine's atomic parameter store; message-thread notifications never replay older values. The native application controller serializes audio lifecycle, preset and sample workflows on one control queue.

```sh
python3 -m pip install -r tools/requirements-quality.txt
python3 tools/check_format.py
ruff check hardware tests tools
ruff format --check hardware tests tools
python3 -m unittest discover -s tests -p test_electronics.py
cmake -S . -B build-sanitize -DCMAKE_BUILD_TYPE=Debug -DRMX_BUILD_NATIVE=OFF -DRMX_SANITIZER=address
cmake --build build-sanitize --parallel 4
ctest --test-dir build-sanitize --output-on-failure
```

Python tooling requires Python 3.11+. Use `RMX_SANITIZER=thread` in a separate build directory for race checks. Plugin builds also run the processor state regressions, including panic/release resets and automation superseding deferred notifications. Physical audio-device and hardware validation remains separate.

### Performance checks

```sh
./build/rmx_benchmark 2000 --csv benchmark.csv
./build/rmx_benchmark 10000 --quick --csv benchmark-48k.csv
./build/rmx_hardware_profile 48000
```

The default benchmark covers 25 workloads at 44.1/48/96 kHz and 32/128/512 frames: all scenes, bypass, release effects, capture bursts, 32 voices, dense events, automation, auto tempo, variable blocks, silence tails and combined effects/voices/capture. It reports p99, p99.9, maximum deadline use and wall-time overruns. `--rate` and `--block` select a configuration; `--strict-max` additionally rejects any overrun. The default p99 gate is 50% of the deadline. CI retains CSV results for each platform. Offline timing includes OS scheduling and does not establish live-device or MCU deadline compliance.

Plugin sample banks use a fixed three-slot handoff and share unchanged immutable samples. Imports coalesce while playback is stopped; the callback never allocates, locks, reference-counts or deletes assets. Regression tests cover stopped imports, concurrent replacement and reclamation outside the callback. DSP caches settled control transforms, keeps roll history warm, and drains reverb tails before sleeping. Manual tempo does not run onset analysis; enabling Auto BPM starts a fresh analysis window.

## Status

Still in development. Mac-only rekordbox audio has been tested, and universal Mac artifacts build. Intel runtime testing, DAW validation, physical FLX routing, long sessions and hardware sound comparisons remain open. The latest capture restart changes need a live check.

The engine uses stereo floating-point audio, with checks at 44.1, 48, 88.2 and 96 kHz. Processing is preallocated; the core audio callback does no allocation, locking, file I/O or UI work. See [validation](docs/validation.md) and [specifications](docs/specifications.md) for the details.

## Reference

[Controls](docs/controls.md) / [Routing](docs/routing.md) / [Specifications](docs/specifications.md) / [Validation](docs/validation.md) / [Standalone hardware and CAD](hardware/README.md)

The original browser prototype remains in `web/`; see its [guide](docs/legacy-prototypes.md). The Swift tap/player prototype was retired because it allocated and locked in its audio callback. The native app and plugin adapters use the shared C++ engine.

## Assets and licensing

Factory drums are synthesized by this project. The panel uses a [Pioneer DJ reference photograph](https://www.pioneerdj.com/product-images/847/38473749-de98-4b65-aedd-a1c68374c1e4/rmx-1000_1.png), recoloured with the visible manufacturer/model badges replaced. The photograph is a third-party asset; these changes do not grant redistribution rights. No project-wide distribution license is asserted for the original repository or third-party assets.
