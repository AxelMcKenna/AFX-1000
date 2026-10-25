# AFX-1000

[![Build](https://github.com/AxelMcKenna/afx-1000/actions/workflows/build.yml/badge.svg)](https://github.com/AxelMcKenna/afx-1000/actions/workflows/build.yml)
![macOS 12+](https://img.shields.io/badge/macOS-12%2B-222222?style=flat-square&logo=apple&logoColor=white)
![Standalone / AU / VST3](https://img.shields.io/badge/Standalone-AU_%2F_VST3-222222?style=flat-square)
![C++20](https://img.shields.io/badge/C%2B%2B-20-167d8d?style=flat-square)
![Hardware prototype](https://img.shields.io/badge/Hardware-B1_prototype-d69a36?style=flat-square)

<img src="assets/readme-hero.svg" alt="AFX-1000. Charcoal housing viewed straight on, with blue drum pads, green/yellow/red level meters, ribbed knobs and recessed controls." width="100%">

**AFX-1000** is a take on the RMX-1000, built around a shared C++20 audio engine. Native Mac app, AU and VST3, with a hardware-style amber/teal panel. A standalone Daisy Seed version is in development too.

Use it with rekordbox through app capture or an audio interface. The effects and factory drums are original implementations. Matching the reference unit's sound, timing and full feature set is still work in progress.

## What's in it

- **Scene FX:** BPF Echo, Echo, Noise, Spiral Up, Reverb Up, HPF Echo, LPF Echo, Crush Echo, Spiral Down and Reverb Down.
- **Isolate FX:** three bands, with Isolator, Cut/Add, Trans/Roll and Gate/Drive modes.
- **X-Pad:** four internal drums and four sample banks, 16 bank variants, WAV import, pitch, rolls, hold and overdub.
- **Release FX:** Back Spin, Echo and Vinyl Brake.

Auto BPM, tap tempo, quantized rolls, assignable X-Pad divisions including triplets, MIDI learn, soft takeover and DAW automation are included.

Loop tempo and pitch have separate playback controls. AUTO can follow detected beat phase, and MIDI clock supports Start, Stop, Continue and Song Position Pointer. See [sync](docs/synchronization.md) and [sample stretching](docs/sample-stretching.md) for the implementation limits.

Overdub runs a four-beat pattern. Each bank holds 16 seconds of audio; slot 1 supports BPM-tagged loops. Sample editing includes trim, reverse, normalization and BPM/loop settings. Pad one-shots trigger immediately.

### Latest sound pass

Rebuilt kick, snare, clap and hat voices, with independent gain, decay and envelope choices. Noise now has a resonant filter sweep, shaped modulation and a damped echo return. Faster pitched playback uses a band-limited reader; a linked stereo peak limiter catches output overshoots.

Pitch travel has separate up/down ranges from 1 to 24 semitones. The extra range is a project extension. These changes are implemented, but have not been matched against recordings of an RMX-1000. [DSP notes](docs/dsp-model.md) cover the details and limits.

## Hardware design

The A08 housing model includes a 334 × 157 × 38 mm chassis, all 29 guided buttons, ten shaft-mount knobs, selector caps, optical inserts and the release mechanism. The print pack exports each part separately and includes a 3MF inventory with the required quantities.

[![A08 CAD overview: assembled housing, integrated controls, printable parts and button mechanism cutaway](docs/assets/hardware/cad-overview.png)](docs/assets/hardware/cad-overview.png)

See the [editable CAD and rebuild instructions](hardware/cad/a08/README.md) and [printer handoff](hardware/cad/a08/PRINTING.md). Geometry and motion checks are recorded by the exporter; physical print fit, return force, optics and full electronics assembly remain to be validated. A08 is separate from the active B1 budget hardware prototype in the [hardware guide](hardware/README.md).

## Run it

Requires macOS 12+, Xcode Command Line Tools and CMake 3.24+. The default native app needs no third-party SDK. Ableton Link is optional and disabled by default.

```sh
git clone git@github.com:AxelMcKenna/afx-1000.git
cd afx-1000
./build-app.sh
open build/RMX.app
```

**Cmd+,** opens audio setup. Pick an input and output, then start audio.

Audio setup remembers devices, channel pairs and buffer size. A previously active route can resume on launch when its devices are available. **Stop Audio** disables that automatic resume.

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

To render 21 drum/pitch/roll and Noise audition clips without opening an audio device:

```sh
cmake --build build --target rmx_sound_preview --parallel 4
./build/rmx_sound_preview build/sound-audition
```

Choose a new output directory each time. These clips use the current engine; they are not recordings of the original hardware.

</details>

## Status

| Area | Current state |
| --- | --- |
| Native Mac audio | Direct rekordbox capture and speaker output have worked in a live session. The latest saved-route/restart behavior still needs a live check. |
| AU / VST3 | Build locally. Earlier universal artifacts include Apple Silicon and Intel slices; the latest sound review builds are arm64. Full DAW validation and Intel runtime checks remain open. |
| Engine and firmware | Local validation records report 26 passing Release checks and an ARM firmware cross-build. Linux ARM CI exposed an exact-float interpolation assertion; its rounding-tolerance fix awaits a CI rerun. Earlier sanitizer and plugin-probe results are recorded separately. |
| Synchronization | AUTO, tap, host transport and MIDI clock are implemented. Optional Link needs its SDK; enabled builds and peer synchronization remain unverified. |
| Sound matching | Latest drum/Noise changes are ready for listening. No reference-unit comparison or claim of identical effects. |
| Live use | Physical FLX4/FLX6 routing, cue separation, a live two-hour soak and measured round-trip latency remain open. |

The engine uses stereo floating-point audio and preallocated processing buffers. The core audio callback does no allocation, locking, file I/O or UI work. Signal checks cover 44.1, 48, 88.2 and 96 kHz. Results belong to the revisions and configurations documented in [validation](docs/validation.md); they do not establish MCU deadlines or hardware-equivalent specifications. See [specifications](docs/specifications.md) for the remaining measurements.

### Hardware

**[B1: 5 V budget prototype](hardware/budget/README.md)** is the active standalone design:

- Daisy Seed with 64 MB SDRAM, physical controls, touch strip, SD loading and watchdog-qualified relay bypass.
- Pin-connected KiCad schematics, BOM and a routed 100 x 100 mm four-layer audio/power/bypass carrier. Recorded native ERC and DRC are clean; draft Gerbers and drill files are included for engineering review.
- Split panel STL files, seam joiner, shaft coupon, DXF/SVG and OpenSCAD enclosure source. Full tray/control solids and assembled fit still need validation.
- Boot-time sample banks, User settings and ADC calibration, plus a 50 ms startup fade. Firmware cross-builds with pinned dependencies and checked ELF placement; it has not been flashed or measured on a board.

The provisional cost ledger is **NZ$295.77**, assuming free printing, DIY assembly and reused power/cables. It is not a confirmed delivered basket. B1 targets consumer line levels and does not retain the original's high-level analogue headroom. The earlier [A0.2 higher-headroom carrier](hardware/electrical/README.md) is a separate design.

**No hardware has been ordered or assembled.** Audio performance, relay fault timing, power/thermal behavior, card I/O and physical fit remain unmeasured. Draft fabrication files are not a production release. Start with the [hardware guide](hardware/README.md) and [clone roadmap](docs/clone-roadmap.md).

```sh
./build/rmx_memory_budget
python3 tools/generate_hardware.py --check
./build/rmx_card_export Performance.rmx /path/to/new-card-folder
```

The exporter writes the project's card layout. `--settings-only` exports User settings without needing audio files; `--samples-only` exports samples. Original RSD/SD interoperability, USB MIDI, live card insertion and complete lighting feedback remain unfinished. See the hardware guide for supported formats and calibration instructions.

## Reference

[Controls](docs/controls.md) / [Routing](docs/routing.md) / [Specifications](docs/specifications.md) / [Validation](docs/validation.md) / [Hardware](hardware/README.md) / [Roadmap](docs/clone-roadmap.md)

[Mac packages](docs/release.md) / [Reference captures and runtime checks](docs/reference-validation.md) / [Engineering update](docs/engineering-update-2026-10-22.md)

The original Swift and browser prototypes are kept in `Sources/` and `web/`. Their guide is [here](docs/legacy-prototypes.md).

## Assets and licensing

Factory drums and the current panel artwork are made by this project. The native and plugin interfaces use a panel generated from [drawing code](tools/generate_panel.mm), with no manufacturer photograph in current builds. A project license is still pending. JUCE, optional Link and embedded dependencies retain their own terms; see [source and dependency notices](THIRD_PARTY_NOTICES.md).
