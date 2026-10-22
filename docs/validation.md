# Validation record

Verified during development on Apple Silicon macOS 26.6.2:

- Native macOS application builds, opens, enumerates audio/MIDI devices, and starts output.
- Direct rekordbox process capture and Mac speaker output started at 44.1 kHz; the user confirmed audio and effects were working.
- JUCE 8.0.6 standalone, AU, and VST3 artifacts compile and link locally. This is not DAW certification.
- Universal native app, AU, and VST3 builds contain both arm64 and x86-64 slices. The native app's minimum binary deployment target is macOS 12.0; application capture requires 14.2+. Intel runtime testing remains outstanding.
- Engine tests cover neutral stereo, wet-only null, all ten Scene FX producing a changed output, the four isolator modes at 44.1/48/88.2/96 kHz, release resets, sampler playback, invalid values, state round trips, WAV, event queue behavior, all shared panel actions, and Scene FX hit areas.
- Synthetic pulse tests at 90/120/128/150/173 BPM lock within 2.5 BPM; observed errors were below 1 BPM. Performance on arbitrary music and tempo changes needs listening and additional fixtures.
- Allocation tracking found no allocations during variable-size audio processing with input roll and band rolls active.
- Live UI automation exercised all 10 Scene FX choices, four isolator modes, four pads, mode/source toggles, Default/User, all exposed sliders, release selection/lever, tap, and nudge. Read-back values confirmed the changes. Audio was stopped during this UI sweep; signal behavior is covered separately by engine tests.
- The benchmark covers all 40 Scene/Isolate combinations, positive/negative knob settings and pad triggers. Run `rmx_benchmark` for the current code and machine; the latest result is recorded below.

Outstanding: physical FLX4/FLX6 routing and headphone separation, a live two-hour soak, loopback latency/noise/distortion measurements, DAW-host automation/validation, Intel Mac runtime checks, ARM Linux runtime performance, and reference-unit sonic comparisons.

A subsequent direct-capture restart timed out in desktop automation, followed by automation failures on other applications. Audio initialization now runs on a separate control queue and reports progress so a slow system call cannot block the interface. The new live restart path still needs verification; the automation failure does not establish its cause.

Do not describe this build as a certified hardware emulation or as fully qualified for live sets based only on the synthetic checks.

## Clone implementation checks, 22 October 2026

The native app and core were rebuilt after adding the four-beat sequencer, physical-control decoder and SDRAM allocation support. `ctest --test-dir build --output-on-failure` now includes:

- Original engine checks.
- Parity regressions: immediate one-shots with Quantize enabled; four-beat playback relative to the first hit; Overdub-off deletion; lane mute/delete without deleting other lanes; Noise with both FX sources disabled; Release routing around an unselected sampler bus; configurable User release retention; quantized roll starts; tap/nudge control behavior; bank identity across playback; host seek recovery; live-input capture after the touch and release fade; physical Bank/Delete/Mute chords; contact debouncing, neutral analog center and touch disconnect.
- Isolate signal checks: all neutral modes and gain endpoints, exact Add impulse taps, detected-kick reduction versus sustained bass, residual filters, Trans rates, forward Roll acquisition, Gate envelope behavior and User defaults.
- Scene signal checks: neutral Main; Noise level/filter/side-chain; Echo arrival and feedback independent of Sub2; source filtering; resonance None; room timing; reverb level/filter roles and all filter types; Spiral pitch; every assignable Echo beat in all four regions at 40 BPM; Default/User delay switching through the engine; Echo width; per-effect state/default compatibility; extreme User settings at 44.1/48/96 kHz.
- Hardware manifest/CAD consistency checks when Python is available.
- A real bounded-arena allocation check: 48 kHz engine buffers use 26,721,456 bytes; engine plus project factory samples use 29,716,656 bytes; engine plus four internal drums and 64 seconds of stereo bank storage use 51,896,496 bytes. Replacement peaks at 51,957,936 bytes inside the 62,914,536-byte usable arena. Frees coalesce and exhaustion throws rather than using the internal heap. Every Scene/Isolate combination plus live roll is processed without arena allocations.

These byte counts are from the 64-bit host ABI; the ARM static-object/map checks are recorded below, while a target allocation trace remains unmeasured. They do not establish MCU deadlines. The mechanical generator checks 46 faceplate features, minimum clearances, screw-boss keepouts, unique GPIO assignments, SDMMC reservations and consistency of generated CAD/firmware files. The generated panel PNG was visually inspected. OpenSCAD solid rendering and physical board tests remain unverified; the successful ARM cross-build is recorded below.

The native User editor was inspected with live UI automation: the long form scrolls, named room choices open correctly, and the bottom controls remain reachable. The later delay/filter additions use the same generated controls and have build/signal coverage; those added rows have not had a separate UI sweep. No fresh live audio sweep is claimed. Final standalone, AU and VST3 artifacts compiled and linked after the engine/UI changes; no DAW runtime certification is implied. Original outstanding live/DAW/reference checks above still apply.

The shared fractional-delay implementation fixes a real buffer overrun found by AddressSanitizer in Spiral. The full six-suite AddressSanitizer/UndefinedBehaviorSanitizer run passed after the fix, including direct one-ULP wrap regression cases and extreme Scene settings. Per-sample smoothing now updates only the 12 consumed performance controls; advanced selectors are applied at block boundaries. The final 1,000-block-per-combination host benchmark reported worst p99 at 1.34% of the 48 kHz/128-frame deadline. Native and universal AU/VST3/standalone builds passed all six suites; `lipo -archs` confirmed arm64 and x86-64 slices in the universal native app, AU and VST3. These are desktop measurements, not embedded performance claims.


## Sampler playback implementation, 22 October 2026

The seventh CTest suite, `sampler`, verifies slot-1 loops in all four banks, one-shot completion including one-frame assets, fractional wrapping with steps larger than the whole sample, loop-pad start/stop without stacked voices, sample-rate/pitch/host-tempo conversion, Panic, metadata roundtrips and legacy defaults. Invalid slot/BPM metadata is rejected; bank duration tests accept exactly 16 seconds and reject an overflow of one frame. Native/plugin imports and preset installation use the same validator.

Native and plugin sample editors now expose mode/BPM. Their current builds pass; these added controls have not had a completed interactive sweep. Native RMX was relaunched after observing Audio stopped; controls were then changing during UI inspection, so no audio playback/settings changes were applied for this check. Fresh live loop listening, plugin dialog runtime validation and original-unit timing/pitch comparisons remain outstanding.

The current bounded-arena check peaks at 51,957,936 bytes with all 64 seconds and separate internal drums installed and processes four active sampler loops plus live roll without allocations. The global-allocation test also covers a sampler loop with band rolls and input roll. This does not establish MCU deadlines or physical SD operation.

All seven suites passed in native Release, plugin and universal build trees, and under AddressSanitizer/UndefinedBehaviorSanitizer (48.12 seconds for the sanitizer run). Native/AU/VST3/standalone artifacts rebuilt successfully. The post-change 1,000-block benchmark across all 40 Scene/Isolate combinations reported worst p99 at 1.42% of the desktop deadline; it is not an MCU measurement.


## ARM firmware cross-build, 22 October 2026

The Daisy adapter and shared Engine/Isolator/Scene code compile and link using Arm GNU 14.3.Rel1 and libDaisy 8.1.0 at commit `9498417add4a4c76bc10737d5e9f43750a4da639`, with the five build submodules at their exact pinned commits. The official compiler package's SHA-256 matches Arm's published checksum. Local payload extraction and SDK bootstrap avoid a global tool installation. Shell DNS remains unavailable; official archives were obtained through the browser.

`tools/check_firmware.py` inspects the actual ELF header, CPU/FPU attributes, allocated sections and required storage symbols. The QSPI vector is at 0x90040000; the 62,914,560-byte audio arena is at 0xc0000000. The image uses 160,324 bytes of QSPI, 40,424 bytes of AXI SRAM and 16,704 bytes in the DMA region. The checker records current project/SDK source hashes, SDK library hash, ELF/bin/map hashes and rejects stale records. See `firmware/daisy/build-record.json` and the reproduction commands in `hardware/README.md`.

This supersedes earlier statements that an ARM cross-build was unavailable. It does not establish successful boot, converter behavior, stack high-water, MCU callback deadlines, SD/USB firmware support or any physical board test. Upstream startup FP-register, nosys-stub and RWX-segment diagnostics remain documented. The project's misleading-indentation warning in touch edge handling was fixed without changing behavior.

The archive bootstrap was also exercised with the pinned macOS compiler package, and the resulting compiler/SDK passed the artifact check again. The native Release build and all seven existing CTest suites passed after the firmware warning cleanup.

OpenSCAD remains unavailable: Chrome blocked the official universal snapshot download as unverified. The browser block was not overridden. Enclosure solid export/inspection is still pending; the existing panel DXF/SVG and manifest checks do not prove the full 3D assembly.


## SD sample loading and export, 22 October 2026

The `card_storage` suite adds real PCM/manifest decoding and exporter roundtrips. It covers 16/24-bit mono/stereo, fragmented reads, odd chunks/data-before-format, truncation and unsupported headers; transactional bank replacement, empty slots/banks, close/read/open failure, allocator mismatch, exact bank limits and bounded-memory exhaustion. The full 64-second replacement, including separate internal drums, peaks at 58,040,496 bytes in the real 60 MiB host arena. Playback of the loaded loop adds no allocations.

The Daisy image links the same decoder with a FatFS adapter. Card/file/bounce storage is global, aligned AXI SRAM; decoder stack buffers are isolated from DMA. The linker verifier checks the actual card object placement and records the new firmware sources. Sample loading and unmounting finish before audio starts. Original RSD format, SD effect presets and physical card/DMA/boot tests remain unverified.

The exporter writes only sample banks and loop/BPM metadata. It requires a fresh output folder, 48 kHz sources within PCM range, and writes the project `RMX/SAMPLES.TXT` plus stereo PCM24 WAVs. A failed export leaves no partial output; an existing destination is rejected. Host roundtrips use the same parser/decoder that compiles into the firmware, not the desktop's general WAV reader.

All eight Release and universal CTest suites pass. The full sanitizer run passed after initial SD integration (49.75 seconds); the final card suite was rerun under AddressSanitizer/UndefinedBehaviorSanitizer after adding empty-bank and overflow/error cases and passed. The final Daisy image uses 190,616 QSPI bytes, 48,408 AXI SRAM bytes and 18,204 DMA-region bytes. The linked card object is 5,952 bytes at 0x24000640, aligned to 32 bytes; the firmware artifact/source and placement checks pass. The command-line exporter was also run on the repository's Spiral Build preset and produced a manifest plus all sixteen PCM24 WAVs.


## Separate internal and bank sources, 22 October 2026

Internal drums now occupy four independent assets; bank imports and SD replacement cannot overwrite them. Regression checks verify queued and sample-offset hits retain their selected source/bank, existing internal/bank voices coexist, mixed-source overdubs replay correctly after selection changes, loop-pad presses start/stop/restart and recorded stops replay. Physical-control checks cover repeated-bank return to internal drums and Hold+pad silent selection without toggling Hold; legacy presets retain bank playback. Internal sources remain project-synthesized substitutes.

All eight suites pass in native Release and universal builds, and under AddressSanitizer/UndefinedBehaviorSanitizer (50.45 seconds). Native, JUCE standalone, AU and VST3 artifacts rebuilt; the native universal executable contains arm64 and x86-64 slices. The Daisy firmware cross-build and current-source/artifact verification pass: 192,068 QSPI bytes, 49,624 AXI SRAM bytes and 18,204 DMA-region bytes, with 25,728-byte engine and 800-byte bank static objects. The 60 MiB audio arena still accommodates full-bank replacement with the four internal drums retained. None of these checks establish physical board execution, original factory sample equivalence, reference-unit bank availability/LED behavior or a new live rekordbox capture/restart test.


## Assignable X-Pad layout and firmware dependencies, 22 October 2026

Eight independent User assignments now cover all sixteen documented X-Pad beat choices, including triplets and eight-beat rolls. `x_roll` retains its eight-position parameter domain; legacy presets keep the previous default divisions. Native/plugin strip labels resolve the active Default/User assignments. Signal fixtures measure emitted one-frame sample repeats for every division, quantized triplet starts against host beat phase, embedded touch/release, preset recall and twelve-second input capture/replay at 40 BPM. This does not implement held live-roll division changes, Slip/Divide modes or gesture overdub, and the new labels have not had an interactive UI sweep.

The native and universal builds pass all ten CTest suites. The nine existing suites, including the new X-Pad signal suite, pass under AddressSanitizer/UndefinedBehaviorSanitizer (53.59 seconds); the subsequently added Python dependency suite also passes in that build tree. Native, standalone, AU and VST3 artifacts rebuilt. Current host allocation counts above include the expanded capture buffer; full SD-bank replacement peaks at 58,040,496 bytes inside the 62,914,536-byte usable arena.

An incremental firmware build exposed a real dependency bug: eager `CPPFLAGS :=` expansion erased the per-object `-MF` filename, leaving C++ headers untracked. The adapter now preserves recursive flag expansion and overrides the SDK's exception/RTTI/unwind defaults with final compiler flags. All C++ objects rebuilt with dependency files. The checker rejects absent/stale translation units, modified makefiles and unlinked objects, and records object/dependency content hashes. Six temporary-file regression cases cover these failures, escaped dependency paths and preserved-timestamp content changes. The actual stale firmware was rejected before rebuilding; a Make dry run with `Parameters.h` changed schedules both `main.o` and `Engine.o` (plus `Scene.o`).

The corrected ARM image and current record pass: 194,100 QSPI bytes, 49,752 AXI SRAM bytes and 18,204 DMA-region bytes; engine/bank static storage is 25,856/800 bytes. The 60 MiB external arena remains at 0xc0000000. Board boot, cache/DMA behavior, stack high-water, callback deadlines and physical audio remain unverified.
