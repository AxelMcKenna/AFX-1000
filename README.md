<p align="center">
  <img src="assets/readme-hero.svg" alt="RMX - Performance, rewired. Stereo performance effects for macOS." width="100%">
</p>

<p align="center">
  <a href="https://github.com/AxelMcKenna/RMX-1000-Clone/actions/workflows/build.yml"><img src="https://github.com/AxelMcKenna/RMX-1000-Clone/actions/workflows/build.yml/badge.svg" alt="Build and engine checks"></a>
  <img src="https://img.shields.io/badge/status-development_preview-f6b44d?style=flat-square" alt="Status: development preview">
  <img src="https://img.shields.io/badge/macOS-12%2B-65d9cc?style=flat-square&logo=apple&logoColor=white" alt="macOS 12 or later">
  <img src="https://img.shields.io/badge/C%2B%2B-20-65d9cc?style=flat-square&logo=cplusplus&logoColor=white" alt="C++20">
  <img src="https://img.shields.io/badge/formats-Standalone_%C2%B7_AU_%C2%B7_VST3-f6b44d?style=flat-square" alt="Standalone, Audio Unit, and VST3">
</p>

<p align="center">
  <strong>Shape the build. Cut the lows. Roll the moment. Release.</strong><br>
  A native stereo effects processor inspired by the RMX-1000 workflow,<br>
  with original DSP, an amber/teal performance surface, and a portable C++ engine.
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> &nbsp;·&nbsp;
  <a href="#the-performance-surface">Features</a> &nbsp;·&nbsp;
  <a href="#rekordbox--routing">rekordbox</a> &nbsp;·&nbsp;
  <a href="#build-your-way">Builds</a> &nbsp;·&nbsp;
  <a href="#the-details">Docs</a>
</p>

---

## The performance surface

Four sections put the mix under your hands.

| Section | What you can do |
| :--- | :--- |
| **Scene FX** | Move between ten filter, echo, noise, spiral, crush, and reverb effects. Shape depth, beat division, and character. |
| **Isolate FX** | Work the low, mid, and high bands with **Isolator**, **Cut/Add**, **Trans/Roll**, and **Gate/Drive**. |
| **X-Pad** | Play sixteen synthesized factory sounds across four banks, import WAVs, pitch samples, latch rolls, and overdub a repeating 16-beat pattern. |
| **Release FX** | Exit with **Back Spin**, **Echo**, or **Vinyl Brake**, then return to dry audio and reset the performance effects. |

### Built for hands-on control

- **Tempo tools** - automatic detection, tap tempo, manual BPM, nudging, and quantized pad triggers.
- **MIDI mapping** - CC learn, soft takeover, MIDI clock, and pad notes 36–39.
- **Sample editing** - trim, reverse, normalize, and save sample references with presets.
- **Native routing** - choose audio devices and channel pairs, or capture rekordbox directly on supported macOS versions.
- **Host integration** - AU/VST3 parameter automation and DAW transport sync.
- **Realtime DSP** - preallocated processing with no allocation, locks, file I/O, or UI work in the core audio callback.

<details>
<summary><strong>All ten Scene FX</strong></summary>

| Build & lift | Cut & descend |
| :--- | :--- |
| BPF Echo | HPF Echo |
| Echo | LPF Echo |
| Noise | Crush Echo |
| Spiral Up | Spiral Down |
| Reverb Up | Reverb Down |

</details>

## Quick start

**You need:** macOS 12+, Xcode Command Line Tools, CMake 3.24+, and a C++20 compiler. The dedicated native app requires no downloaded library.

```sh
git clone git@github.com:AxelMcKenna/RMX-1000-Clone.git
cd RMX-1000-Clone
./build-app.sh
open build/RMX.app
```

Open **File → Audio & MIDI setup** with **⌘ ,**, select your input and output, then start audio.

| Shortcut | Action |
| :---: | :--- |
| **Space** | Toggle bypass |
| **Esc** | Reset performance effects |
| **T** | Tap tempo |
| **1 · 2 · 3 · 4** | Trigger the four pads |
| **Shift + drag** | Fine knob adjustment |

Double-click a knob for an exact value, or right-click for reset and MIDI learn. See the [full control guide](docs/controls.md) for source selection, rolls, overdub, and release behavior.

## rekordbox & routing

### Mac only · no controller needed

Direct application capture requires **macOS 14.2+**.

1. Open rekordbox and load a track.
2. Open RMX audio setup with **⌘ ,**.
3. Choose **rekordbox - direct app capture** as the input.
4. Choose speakers, headphones, or an audio interface as the output.
5. Start audio, allow macOS audio capture if prompted, and play the track.

RMX processes the captured stereo mix. The temporary route mutes duplicate direct playback while active and restores normal playback when stopped. rekordbox integration uses audio routing; rekordbox does not host the AU/VST3 versions as native effects.

### FLX4 / FLX6

With a stereo audio interface:

```text
FLX MASTER RCA → Interface line inputs → RMX → Interface outputs → Speakers
rekordbox cue → FLX headphone output → Headphones
```

An aggregate device with BlackHole is another routing option. Physical FLX routing and cue/master separation still need testing on the connected controller. Follow the [routing guide](docs/routing.md) for setup and monitoring precautions.

## Under the hood

| | Implementation |
| :--- | :--- |
| **Engine** | Portable C++20, stereo floating-point processing |
| **Checked sample rates** | 44.1 · 48 · 88.2 · 96 kHz |
| **Buffer selection** | 64–128 frames where the audio device supports it |
| **macOS artifacts** | Native app, AU, VST3, and JUCE standalone |
| **Architectures** | Universal arm64 + x86_64 artifacts built; Intel runtime verification pending |
| **Portability** | Headless core builds independently on Linux; desktop audio adapters remain platform specific |

> **Development preview.** Native rekordbox audio has worked in a Mac-only session, and engine/control checks pass. Real-unit sonic matching, physical FLX testing, DAW validation, and long-session qualification remain open. The latest direct-capture restart changes also need a live check. See the [validation record](docs/validation.md) for the evidence and remaining work.

## Build your way

<details>
<summary><strong>AU / VST3 / JUCE standalone</strong></summary>

```sh
cmake -S . -B build-plugins \
  -DCMAKE_BUILD_TYPE=Release \
  -DRMX_BUILD_PLUGINS=ON
cmake --build build-plugins --parallel 4
```

The build fetches **JUCE 8.0.6** from its official repository. To use an existing checkout, add `-DRMX_JUCE_PATH=/absolute/path/to/JUCE`.

Artifacts are written to `build-plugins/RMXPlugin_artefacts/Release/`. The dedicated native app at `build-plugins/RMX.app` provides device-pair selection and direct rekordbox capture.

Comply with JUCE's applicable license before distributing JUCE-based products.

</details>

<details>
<summary><strong>Universal macOS builds</strong></summary>

Use a fresh build directory:

```sh
cmake -S . -B build-universal \
  -DCMAKE_BUILD_TYPE=Release \
  -DRMX_BUILD_PLUGINS=ON \
  '-DCMAKE_OSX_ARCHITECTURES=arm64;x86_64'
cmake --build build-universal --parallel 4
```

Distribution signing and notarization require your Apple credentials. The native build script uses an ad-hoc signature for local use.

</details>

<details>
<summary><strong>Engine checks, benchmarks & offline rendering</strong></summary>

Build the core and tools on macOS or Linux:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 4
ctest --test-dir build --output-on-failure
./build/rmx_benchmark
./build/rmx_render input.wav output.wav
```

Pass a preset as the optional third argument to the renderer:

```sh
./build/rmx_render input.wav output.wav "assets/presets/Spiral Build.rmx"
```

Benchmarks measure engine processing time. They do not measure physical audio round-trip latency, converter noise, or analog distortion.

</details>

## The details

| Guide | Inside |
| :--- | :--- |
| [Controls](docs/controls.md) | Every control, keyboard shortcut, sample workflow, and MIDI mapping |
| [Audio routing](docs/routing.md) | Direct rekordbox capture, FLX4/FLX6, BlackHole, and mixer loops |
| [Specifications](docs/specifications.md) | Software capabilities, performance targets, and future hardware requirements |
| [Validation](docs/validation.md) | Completed checks and outstanding live/hardware verification |
| [Original prototypes](docs/legacy-prototypes.md) | The retained Swift and browser experiments in `Sources/` and `web/` |

### Assets & licensing

Factory drums are synthesized by this project. The interface uses a [Pioneer DJ hardware reference photograph](https://www.pioneerdj.com/product-images/847/38473749-de98-4b65-aedd-a1c68374c1e4/rmx-1000_1.png), with an amber/teal palette and replaced manufacturer/model badges. The photograph remains a third-party asset; visual unbranding does not grant redistribution rights. No project-wide distribution license is asserted for the original repository or third-party assets.

The effects are original implementations inspired by the RMX-1000 workflow. A matching control layout does not establish a matching sound.
