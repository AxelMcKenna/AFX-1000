# AFX-1000

[![Build](https://github.com/AxelMcKenna/afx-1000/actions/workflows/build.yml/badge.svg)](https://github.com/AxelMcKenna/afx-1000/actions/workflows/build.yml)
![macOS 12+](https://img.shields.io/badge/macOS-12%2B-222222?style=flat-square&logo=apple&logoColor=white)
![Standalone / AU / VST3](https://img.shields.io/badge/Standalone-AU_%2F_VST3-222222?style=flat-square)
![C++20](https://img.shields.io/badge/C%2B%2B-20-167d8d?style=flat-square)
![Standalone hardware development](https://img.shields.io/badge/Hardware-Standalone_development-d69a36?style=flat-square)

**Proprietary — all rights reserved.** Original project code, firmware, PCB and housing designs require a separate written license for reuse, builds, manufacture or redistribution. Public access and build instructions do not grant that permission. Third-party licenses and GitHub's applicable platform permissions remain in effect. See [LICENSE](LICENSE) and [dependency notices](THIRD_PARTY_NOTICES.md).

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

Current work targets the full 12 V standalone unit. The [fabrication preparation inventory](hardware/fabrication/README.md) identifies the selected development sources and remaining holds across all functional roles. The [A12 housing work](hardware/cad/a12/README.md) includes the larger enclosure proposal with 20% more depth and height. The integrated unit remains unfinished.

The earlier A11 design has a 334 × 157 × 38 mm chassis, 29 guided buttons, ten knobs, selector caps, optical inserts and the release mechanism. It includes mounts and clearances for its routed main supply and placed E25 disconnect board.

[![A11 housing, controls and internal board placement](docs/assets/hardware/a11-overview.png)](docs/assets/hardware/a11-overview.png)

See the [A11 editable CAD](hardware/cad/a11/README.md), [printer handoff](hardware/cad/a11/PRINTING.md), [electronics and wiring status](hardware/validation/disconnect-placement.json) and [saved review package](docs/reviews/standalone-E25-A11/). The unit is not build-ready: disconnect routing, 5 V distribution changes, remaining boards/wiring and physical qualification are unfinished.

### PCB design

Native KiCad layouts from the standalone electronics work. These are engineering candidates; they have not been manufactured or electrically qualified. Click a layout for the full-resolution image.

**Combined main audio routing and reference plane · 150 × 63 mm · four-layer candidate**

| Top local copper | Bottom local copper, viewed from below |
| --- | --- |
| [![Partial main audio PCB: actual top copper and lands](hardware/fabrication/staging/audio-main-controls-06/plots/top.png)](hardware/fabrication/staging/audio-main-controls-06/plots/top.png) | [![Partial main audio PCB: actual bottom copper and lands](hardware/fabrication/staging/audio-main-controls-06/plots/bottom.png)](hardware/fabrication/staging/audio-main-controls-06/plots/bottom.png) |

The [six-section audio candidate](hardware/fabrication/staging/audio-main-controls-06/README.md) retains **328 assigned electrical footprints**, including four bare test pads, and six proposed mounts. **All 131 declared local signal/supply endpoints and all 200 placed ground pads are native-connected.** Opens have fallen from 724 to **208**, including 57 verified low-speed control joins and 17 retained earlier control pairs. Its 2,425 tracks and 382 conventional vias preserve every amplifier placement and direct compensation capacitor track. The watchdog and settling-supervisor cells have renewed receiving; their private timing paths are connected, and the settling pull-up is local to its driver. Further codec-run/timer-ready, bypass-sense/bias-window and ANALOG_OK branches retain every component pose and earlier copper object; the longer controls still require installed timing/noise/loading qualification. Native geometry and ERC findings remain zero with all categories enabled. **The ESS codec footprint is missing and global routing is unfinished.** Full parts/process, analog, power/thermal and assembly verification remain open.

The newer, unselected [CODEC_PGOOD comparison with four copper views](hardware/fabrication/staging/audio-main-controls-08/README.md) reaches **203 opens and two remaining control gaps**. It retains the [205-open bypass rework](hardware/fabrication/staging/audio-main-bypass-repack-04/README.md), adds a short CHIP_EN bridge and completes the power-good branch after an independently checked SENSE-entry reroute. Native geometry/ERC are 0/0 with all earlier checked terminals retained. SENSE accuracy/noise, the earlier long INPUT_ENABLE repair and installed performance remain review holds; it is not a fabrication release.

The unselected [six-layer local-routing trial](hardware/fabrication/staging/audio-main-six-local-01/README.md) reaches **180 opens with the control nets connected**. A dedicated signal layer and additional AGND plane first close the remaining control routes; 21 short surface links then complete six buffer feedback loops and local passive connections without adding more vias. Native geometry/ERC remain 0/0, and the local delta audit preserves all existing copper and 930 native pad shapes.

The [173-open comparator-input trial](hardware/fabrication/staging/audio-main-six-monitor-01/README.md) adds seven bias-window input joins. Its original enlarged-spacing review is superseded: a 0.5 mm search radius missed four relationships that violated the intended 0.71 mm policy. Native DRC/ERC and connection counts were unaffected; the [measured erratum](hardware/fabrication/staging/audio-main-six-monitor-03/previous-spacing-erratum.json) records the defect.

The newer [GAIN_REQ clearance rework and all six copper views](hardware/fabrication/staging/audio-main-six-monitor-03/README.md) reaches **172 opens**. It renews the obstructing digital branch with one standard via and bridges the right bias input without another hole. A separate exhaustive check measures **14,303 pairs across all 41 comparator-input tracks** and finds no violations of the 0.71 mm trace-centreline policy. All unretired geometry, 930 native pad shapes and earlier connection witnesses remain intact; native geometry/ERC are 0/0. The earlier layer-conversion audit checks all 19 keepouts and native inner lands. **The physical stack/cost is unapproved, U201 is missing, electrical noise/fault performance is unqualified and the wider analogue routing remains incomplete.** The selected four-layer checkpoint above is unchanged.

| Actual In3 routing, renewed GAIN_REQ branch in cyan | Actual additional In4 AGND copper |
| --- | --- |
| [![Unselected six-layer audio rework: actual signal copper](hardware/fabrication/staging/audio-main-six-monitor-03/plots/signals.png)](hardware/fabrication/staging/audio-main-six-monitor-03/plots/signals.png) | [![Unselected six-layer audio rework: actual additional ground plane](hardware/fabrication/staging/audio-main-six-monitor-03/plots/ground2.png)](hardware/fabrication/staging/audio-main-six-monitor-03/plots/ground2.png) |

[![Actual inner AGND reference copper, sensitive-node openings and mounting exclusions](hardware/fabrication/staging/audio-main-controls-06/plots/ground.png)](hardware/fabrication/staging/audio-main-controls-06/plots/ground.png)

All **161 placed supply/sense pads** now connect to their designated source through inner and outer copper. Native-refilled ground retains all 200 ground connections. Missing codec lands and complete capacity/drop/return qualification remain open.

[![Actual partial In2 supply routing](hardware/fabrication/staging/audio-main-controls-06/plots/supplies.png)](hardware/fabrication/staging/audio-main-controls-06/plots/supplies.png)


| E12 ADC driver · 110 × 78 mm | Main supply candidate · 90 × 44 mm |
| --- | --- |
| [![E12 ADC driver top copper and component outlines](docs/assets/hardware/e12-adc-layout.png)](docs/assets/hardware/e12-adc-layout.png) | [![Main supply candidate top copper and component outlines](docs/assets/hardware/main-power-layout.png)](docs/assets/hardware/main-power-layout.png) |
| [Editable PCB and routing checks](hardware/electronics/adc_driver/pcb/) | [Editable PCB and routing checks](hardware/electronics/power_supply/routing/) |

**E26 disconnect pilot · 156 × 45.25 mm**

[![E26 six-rail disconnect pilot top copper, vias and component outlines](docs/assets/hardware/e26-disconnect-layout.png)](docs/assets/hardware/e26-disconnect-layout.png)

The pictured E26 checkpoint has **21 open connections and 30 native DRC warnings**. The ADC driver is a separate characterization board, and the main supply shown predates the proposed P02 source redesign. These layouts do not yet form one integrated assembly. See the [E26 source and findings](hardware/electronics/rail_disconnect/revision26/) and [current development handoff](hardware/DEVELOPMENT.md).

The [three-board qualification review](hardware/validation/board-qualification/README.md) identifies additional electrical/layout failures, a separate ADC repair trial and a new disconnect routing candidate. **Qualification is withheld for all three pictured boards; they are not fabrication-ready.**

**E28 protection-board checkpoint · 156 × 60 mm · eight layers**

[![E28 protection board: actual checked top copper, silkscreen and outline](hardware/electronics/rail_disconnect/revision28/generated/low-power-run-work/generated/native-signal-stub-cleanup-06/closed-top.svg)](hardware/electronics/rail_disconnect/revision28/generated/low-power-run-work/generated/native-signal-stub-cleanup-06/closed-top.svg)

The pictured E28 checkpoint has zero open connections, zero hard DRC errors and zero ERC/parity findings, with all native rule categories enabled. It retains 52 warnings. A newer candidate removes ten geometrically redundant track objects and has 49 warnings, with the same zero opens/hard errors/ERC/parity findings. See the [current fabrication inventory](hardware/fabrication/README.md) and [pictured checkpoint review](hardware/qualification/boards/aux_low_power_run/CLOSED_LAYOUT_REVIEW.md). Manufacturing, P03 interface acceptance and physical qualification remain open. This is an actual KiCad plot, not manufactured hardware or a fabrication release.

**Matching P03 source with integrated RUN transmitter · 160 × 45 mm · six layers**

[![P03 source with integrated AX03 transmitter: actual checked top copper and component bodies](hardware/electronics/power_distribution/p03/candidates/ax03-run-transmitter/generated/native-closed-transmitter/closed-top.svg)](hardware/electronics/power_distribution/p03/candidates/ax03-run-transmitter/generated/native-closed-transmitter/closed-top.svg)

The separate 264-part P03 candidate has zero native DRC errors, warnings, opens, ERC and parity findings. Its [integration review](hardware/qualification/boards/aux_low_power_run/P03_INTEGRATION_REVIEW.md) records the actual local bypass paths, E28 pin map and outstanding manufacturing, harness and physical qualification. Canonical P03 and the preserved source projects remain unchanged; the complete unit is not fabrication-ready.

**Sequenced stereo bypass candidate · 110 × 55 mm · four layers**

[![E11 sequenced bypass: checked top copper, relay and logic placement](hardware/fabrication/staging/bypass-closed-native-03/plots/top/top.svg)](hardware/fabrication/staging/bypass-closed-native-03/plots/top/top.svg)

The new E11 layout contains 55 circuit parts and four mounts, with zero native DRC, ERC, schematic-parity or connectivity findings. It retains the independent input-settling and fresh-permit bypass circuit. The [source-bound handoff](hardware/fabrication/staging/bypass-closed-native-03/handoff.json) and [package corrections](hardware/fabrication/package-review.md) record the checks and limits. Installed fit, exact parts/connectors, assembly process and measured operation remain unqualified.

**Eight-window rail monitor candidate · 80 × 70 mm · four layers**

[![E13 rail monitor: actual checked top copper and all 181 circuit parts](hardware/fabrication/staging/rail-monitor-reserved-closed-native-02/plots/top/top.svg)](hardware/fabrication/staging/rail-monitor-reserved-closed-native-02/plots/top/top.svg)

The selected E13 layout preserves the original 181-part circuit and four mounts, with **zero native DRC, ERC, schematic-parity or connectivity findings**. Reserving the supply escapes and adding 3.3 V branches on the inner supply layer closed routing while retaining the dedicated ground plane. The [bottom copper](hardware/fabrication/staging/rail-monitor-reserved-closed-native-02/plots/bottom/bottom.svg), [supply copper](hardware/fabrication/staging/rail-monitor-reserved-closed-native-02/plots/supply/supply.svg), [source-bound handoff](hardware/fabrication/staging/rail-monitor-reserved-closed-native-02/handoff.json) and [drill-to-SMD screen](hardware/fabrication/staging/rail-monitor-reserved-closed-native-02/smd-drill-review.json) are available for review. Precision parts, power/noise review, installed fit and assembly/process acceptance remain open. This is a development layout, not a fabrication release.

<details>
<summary>3D bare-board preview · E12 ADC driver</summary>

![Native KiCad 3D render of the unpopulated E12 ADC driver PCB](docs/assets/hardware/e12-adc-3d.png)

An unpopulated board rendered directly from the KiCad PCB. This is a CAD preview, not a photograph of manufactured hardware.

</details>

The [F06 standalone firmware candidate](hardware/firmware/full_engine/README.md) builds the maintained DSP engine with 152 parameters, bounded SDRAM storage and control-fault recovery. The earlier [preserved runtime and host checks](hardware/runtime/README.md) remain available separately. Earlier [A08 mechanics](hardware/cad/a08/README.md), the [B1 budget prototype](hardware/budget/README.md) and the [A0 enclosure reference](hardware/cad/a0-reference/) also remain separate designs.

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

### Python tooling

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run from the repository root:

```sh
uv sync --locked
uv run --locked python -m unittest discover -s tests/tooling
uv run --locked python -m unittest discover -s tests -p 'a*_integration_tests.py'
```

uv uses Python 3.12 from `.python-version` and creates an ignored `.venv/`. The root `pyproject.toml` declares NumPy, Pillow and trimesh; `uv.lock` pins the resolved environment. Run Python tools with `uv run --locked python ...`. Use `uv add <package>==<version>` to change a pinned dependency, and commit both project metadata and the lockfile.

Configure CMake through `uv run --locked cmake ...` so its Python tests use this environment. An existing CMake build may retain a previously selected interpreter; use a fresh build directory or explicitly set `-DPython3_EXECUTABLE=/absolute/path/to/.venv/bin/python` when reconfiguring.

The six hardware `requirements.txt` files remain frozen dependency snapshots referenced by historical source hashes. New development and CI use the root uv project. OpenSCAD, KiCad and the ARM toolchain remain separate native dependencies; checks that need KiCad's `pcbnew` module still use KiCad's own Python interpreter.

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
uv run --locked cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
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
| Engine and firmware | F06 records 16 passing host groups and clean ARM builds for onboard and external-converter profiles. The source snapshot also records five focused sanitizer groups. Actual MCU timing and hardware operation remain unverified. |
| Synchronization | AUTO, tap, host transport and MIDI clock are implemented. Optional Link needs its SDK; enabled builds and peer synchronization remain unverified. |
| Sound matching | Latest drum/Noise changes are ready for listening. No reference-unit comparison or claim of identical effects. |
| Live use | Physical FLX4/FLX6 routing, cue separation, a live two-hour soak and measured round-trip latency remain open. |

The engine uses stereo floating-point audio and preallocated processing buffers. The core audio callback does no allocation, locking, file I/O or UI work. Signal checks cover 44.1, 48, 88.2 and 96 kHz. Results belong to the revisions and configurations documented in [validation](docs/validation.md); they do not establish MCU deadlines or hardware-equivalent specifications. See [specifications](docs/specifications.md) for the remaining measurements.

### Hardware

**[B1: 5 V budget prototype](hardware/budget/README.md)** is the separate budget standalone design:

- Daisy Seed with 64 MB SDRAM, physical controls, touch strip, SD loading and watchdog-qualified relay bypass.
- Pin-connected KiCad schematics, BOM and a routed 100 x 100 mm four-layer audio/power/bypass carrier. Recorded native ERC and DRC are clean; draft Gerbers and drill files are included for engineering review.
- Split panel STL files, seam joiner, shaft coupon, DXF/SVG and OpenSCAD enclosure source. Full tray/control solids and assembled fit still need validation.
- Boot-time sample banks, User settings and ADC calibration, plus a 50 ms startup fade. Firmware cross-builds with pinned dependencies and checked ELF placement; it has not been flashed or measured on a board.

The provisional cost ledger is **NZ$295.77**, assuming free printing, DIY assembly and reused power/cables. It is not a confirmed delivered basket. B1 targets consumer line levels and does not retain the original's high-level analogue headroom. The earlier [A0.2 higher-headroom carrier](hardware/electrical/README.md) is a separate design.

**No hardware has been ordered or assembled.** Audio performance, relay fault timing, power/thermal behavior, card I/O and physical fit remain unmeasured. Draft fabrication files are not a production release. Start with the [hardware guide](hardware/README.md) and [clone roadmap](docs/clone-roadmap.md).

```sh
./build/rmx_memory_budget
uv run --locked python tools/generate_hardware.py --check
./build/rmx_card_export Performance.rmx /path/to/new-card-folder
```

The exporter writes the project's card layout. `--settings-only` exports User settings without needing audio files; `--samples-only` exports samples. Original RSD/SD interoperability, USB MIDI, live card insertion and complete lighting feedback remain unfinished. See the hardware guide for supported formats and calibration instructions.

## Reference

[Controls](docs/controls.md) / [Routing](docs/routing.md) / [Specifications](docs/specifications.md) / [Validation](docs/validation.md) / [Hardware](hardware/README.md) / [Roadmap](docs/clone-roadmap.md)

[Mac packages](docs/release.md) / [Reference captures and runtime checks](docs/reference-validation.md) / [Engineering update](docs/engineering-update-2026-10-22.md)

The historical browser prototype is kept in `prototypes/web/`. Its guide is [here](docs/legacy-prototypes.md). The retired Swift prototype is available in Git history.

## Assets and licensing

Original project material is covered by the [AFX-1000 Proprietary Rights Notice](LICENSE), copyright 2026 Axel McKenna, all rights reserved. It covers the project's original software, firmware, legacy prototypes, PCB and mechanical design files, documentation and assets to the extent the owner holds the relevant rights. Reuse, personal builds, manufacture and redistribution require separate written permission, subject to the exceptions in the notice.

Factory drums and the current panel artwork are made by this project. The native and plugin interfaces use a panel generated from [drawing code](tools/generate_panel.mm), with no manufacturer photograph in current builds. Third-party software, footprints and other supplied material retain their own terms. JUCE and optional Link need a compatible licensing route for distribution; the project notice does not override their copyleft obligations. See [source and dependency notices](THIRD_PARTY_NOTICES.md).
