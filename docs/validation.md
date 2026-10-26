# Validation record

## Linux ARM interpolation assertion, 23 October 2026

The reported GitHub Actions `ubuntu-24.04-arm` run passed 25 of 26 entries and
failed `sampler` at "Neutral loop stretch altered interpolation". That assertion
required bit-identical results from two separately optimized linear-interpolation
expressions. GCC permits floating-point multiply/add contraction by default in
C++, which can change the last rounded bits after inlining; see the
[GCC optimization options](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html#index-ffp-contract).
This is the suspected portability cause, not a measured audio discontinuity.

The assertion now allows two float epsilons (approximately 2.38e-7 full scale)
per channel, retaining its 10,000-frame comparisons at four playback steps.
There is no DSP or compiler-flag change. The updated sampler target compiles and
links with AppleClang on arm64; tests were not executed for this change. The
GitHub Linux ARM rerun remains outstanding. Earlier passing local records below
do not establish a passing CI matrix for this revision.

## Earlier local validation

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

The initial exporter wrote sample banks and loop/BPM metadata; User profile export was added subsequently, as recorded below. Sample export requires a fresh output folder and 48 kHz sources within PCM range, and writes the project `RMX/SAMPLES.TXT` plus stereo PCM24 WAVs. A failed export leaves no partial output; an existing destination is rejected. Host roundtrips use the same parser/decoder that compiles into the firmware, not the desktop's general WAV reader.

All eight Release and universal CTest suites pass. The full sanitizer run passed after initial SD integration (49.75 seconds); the final card suite was rerun under AddressSanitizer/UndefinedBehaviorSanitizer after adding empty-bank and overflow/error cases and passed. The final Daisy image uses 190,616 QSPI bytes, 48,408 AXI SRAM bytes and 18,204 DMA-region bytes. The linked card object is 5,952 bytes at 0x24000640, aligned to 32 bytes; the firmware artifact/source and placement checks pass. The command-line exporter was also run on the repository's Spiral Build preset and produced a manifest plus all sixteen PCM24 WAVs.


## Separate internal and bank sources, 22 October 2026

Internal drums now occupy four independent assets; bank imports and SD replacement cannot overwrite them. Regression checks verify queued and sample-offset hits retain their selected source/bank, existing internal/bank voices coexist, mixed-source overdubs replay correctly after selection changes, loop-pad presses start/stop/restart and recorded stops replay. Physical-control checks cover repeated-bank return to internal drums and Hold+pad silent selection without toggling Hold; legacy presets retain bank playback. Internal sources remain project-synthesized substitutes.

All eight suites pass in native Release and universal builds, and under AddressSanitizer/UndefinedBehaviorSanitizer (50.45 seconds). Native, JUCE standalone, AU and VST3 artifacts rebuilt; the native universal executable contains arm64 and x86-64 slices. The Daisy firmware cross-build and current-source/artifact verification pass: 192,068 QSPI bytes, 49,624 AXI SRAM bytes and 18,204 DMA-region bytes, with 25,728-byte engine and 800-byte bank static objects. The 60 MiB audio arena still accommodates full-bank replacement with the four internal drums retained. None of these checks establish physical board execution, original factory sample equivalence, reference-unit bank availability/LED behavior or a new live rekordbox capture/restart test.


## Assignable X-Pad layout and firmware dependencies, 22 October 2026

Eight independent User assignments now cover all sixteen documented X-Pad beat choices, including triplets and eight-beat rolls. `x_roll` retains its eight-position parameter domain; legacy presets keep the previous default divisions. Native/plugin strip labels resolve the active Default/User assignments. Signal fixtures measure emitted one-frame sample repeats for every division, quantized triplet starts against host beat phase, embedded touch/release, preset recall and twelve-second input capture/replay at 40 BPM. This does not implement held live-roll division changes, Slip/Divide modes or gesture overdub, and the new labels have not had an interactive UI sweep.

The native and universal builds pass all ten CTest suites. The nine existing suites, including the new X-Pad signal suite, pass under AddressSanitizer/UndefinedBehaviorSanitizer (53.59 seconds); the subsequently added Python dependency suite also passes in that build tree. Native, standalone, AU and VST3 artifacts rebuilt. Current host allocation counts above include the expanded capture buffer; full SD-bank replacement peaks at 58,040,496 bytes inside the 62,914,536-byte usable arena.

An incremental firmware build exposed a real dependency bug: eager `CPPFLAGS :=` expansion erased the per-object `-MF` filename, leaving C++ headers untracked. The adapter now preserves recursive flag expansion and overrides the SDK's exception/RTTI/unwind defaults with final compiler flags. All C++ objects rebuilt with dependency files. The checker rejects absent/stale translation units, modified makefiles and unlinked objects, and records object/dependency content hashes. Six temporary-file regression cases cover these failures, escaped dependency paths and preserved-timestamp content changes. The actual stale firmware was rejected before rebuilding; a Make dry run with `Parameters.h` changed schedules both `main.o` and `Engine.o` (plus `Scene.o`).

The corrected ARM image and current record pass: 194,100 QSPI bytes, 49,752 AXI SRAM bytes and 18,204 DMA-region bytes; engine/bank static storage is 25,856/800 bytes. The 60 MiB external arena remains at 0xc0000000. Board boot, cache/DMA behavior, stack high-water, callback deadlines and physical audio remain unverified.


## Boot-time User profiles and octave regression, 22 October 2026

The card exporter now writes `RMX/USER.TXT` with the preset's stored advanced User settings. `--settings-only` avoids loading WAV references; `--samples-only` preserves the sample-only workflow. Exporter-to-firmware-parser roundtrips compare every implemented advanced field, even when the preset's current mode is Default. Invalid User settings reject the staged export without leaving a partial destination.

The shared parser streams at most 16 KiB through caller scratch with 128-byte bounded lines and no allocation. Stable-ID rows accept finite decimal/scientific values and preserve float precision, including host subnormal roundtrips. Unknown/duplicate/non-User fields, invalid ranges and fractional choices are rejected. Read/seek/truncation/adapter-count/format errors preserve the output candidate. Tests verify physical/performance controls remain untouched and a loaded X-Pad assignment changes emitted sample timing only in User mode. The FatFS adapter commits after a successful read and file close, loads samples independently and reports profile errors separately. Actual card reads/close failures and boot behavior still need board testing.

The full build exposed a plain-kick 173 BPM half-time regression in the current incremental tempo tracker. Octave candidates are now compared against the same current window, with half-hop interpolation to reduce lag-grid bias. Tests retain the original engine BPM checks and add plain 173 BPM patterns at four input offsets; busy stereo/phase/silence/tempo-change fixtures remain passing. The octave recheck adds at most four bounded correlations on a sweep's final hop; MCU deadlines remain unmeasured.

All 14 native Release and universal suites pass. The full AddressSanitizer/UndefinedBehaviorSanitizer run passes all 14 suites (64.88 seconds). Native, JUCE standalone, AU and VST3 artifacts rebuilt against the current workspace, including its concurrent Link/panel/transport changes; no runtime Link or fresh live capture validation is claimed here. The 1,000-block benchmark across all 40 effect/mode combinations reports worst p99 at 0.670313% of the desktop deadline. This is a host measurement.

The Daisy firmware and current-source/object/artifact checks pass with the new profile loader and current tempo code: 205,704 QSPI bytes, 47,640 AXI SRAM bytes and 18,204 DMA-region bytes; static engine/bank objects occupy 23,744/800 bytes. The card object remains 5,952 bytes, aligned at 0x24000640. The audio arena remains 60 MiB at 0xc0000000. A command-line settings-only export of the repository's Spiral Build preset produced a 2,618-byte profile with 108 parameter rows and no sample manifest/WAVs. Original SD/RSD interoperability, USB synchronization, live insertion/loading, nonvolatile User storage and physical board qualification remain unfinished.


## NZ sourcing and bypass permission CAD, 22 October 2026

The [NZ sourcing record](../hardware/sourcing-nz.md) records the user's local-sourcing preference and distinguishes the 64 MB Seed's NZ pre-order from verified immediate stock. No purchase has been made. Relay candidates from an NZ storefront dispatch from overseas; most carrier/control/mechanical parts remain unselected.

The earlier nominal 50 ms TPS3431 recommendation was incorrect: TI's adjustable equation has a 55 ms offset and a tested capacitor minimum of 100pF. The new draft uses 120pF C0G 1% (64.288 ms nominal) so negative capacitor tolerance stays inside the tested range. This leaves the 50 ms target unresolved rather than claiming the longer interval meets it.

`hardware/electrical` now contains a generated KiCad schematic with embedded pin-block symbols, matching SVG and 27-part physical BOM (plus two virtual power flags). TPS3808 supervisors monitor 3.3 V/5 V, with a shared manual-bypass input and nominal 300 ms recovery. Health gates asynchronously clear a 74LVC1G74; a fresh heartbeat rising edge is required before relay permission can return. A stalled common heartbeat cannot periodically re-enable permission when the watchdog's low fault pulse ends. The firmware source drives that heartbeat only after completed audio callbacks advance; its execution is still unverified on a board.

The restricted CAD reader reconstructs connectivity from emitted symbols/wires/labels/NC markers rather than importing the generator's JSON nets. Seven tests check selected IC values/pin tables, power and bias connections, all 128 prior-state/current-input combinations, independent faults/recovery, repeated watchdog pulses with frozen high/low heartbeat and broken-clear/clock mutations. Generated artifacts and the panel manifest are consistent. A raster rendering of the SVG primitives was inspected for legibility and overlaps; this was not a native KiCad render. The Release build and all 16 CTest suites passed; the ARM current-source/artifact checker remains passing. After the final unused-pin naming correction, the two bypass suites were rerun.

These are ideal digital logic and generation checks, not KiCad ERC, timing closure, analog simulation or physical fault injection. Native import/ERC, DRB exposed-pad/footprint review, exact NZ-stocked parts, final watchdog selection, relay driver/suppression, line-level circuits, analog rails/mute, PCB layout and complete mechanical integration remain required. No PCB, Gerber release or assembled prototype is claimed.


## Watchdog replacement and startup qualification, 22 October 2026

The A0.1 permission draft supersedes the TPS3431/120pF and single-flip-flop selection above. U21 is now TPS3435AFACADDFRQ1, using its exact pinout A: MR high, SET0 low, 10.1nF CWD and 10nF CRST. Manufacturer specifications verify the selected 10nF/100pF KEMET capacitors as C0G 1%, 50V in 0805/0603 packages. The resulting watchdog interval is 49.995 ms nominal, with 39.596–60.594 ms initial device/capacitor tolerance bounds; the nominal output pulse is 49.5 ms. Capacitor temperature effects, parasitics, output-driver and relay timing still need qualification. This resolves the nominal timing selection, not a maximum complete fault-to-dry limit. The former DRB exposed-pad gate no longer applies to the new DDF package; its replacement footprint still needs review.

The selected suffix has a nominal ten-second startup frame after power-up and each output pulse. A valid falling WDI edge exits that frame early. U24 is now a 74LVC74APW dual flip-flop: both asynchronous resets and clocks are common, stage 1 D is high, stage 1 Q feeds stage 2 D, and only stage 2 Q grants permission. Two fresh rising edges ensure an intervening falling edge starts watchdog monitoring before permission. This also avoids qualifying on an edge at fault-pulse release when the watchdog may have ignored the preceding falling edge. Physical reset recovery, stage setup/hold and clock skew remain unverified.

Eleven bypass tests now read the emitted CAD, cover all 256 prior-two-stage/clock and current-input combinations, validate timing-network connectivity/ranges/tolerances, and use a separate ideal watchdog-frame model. Twelve freeze points across startup, power-good and healthy operation are swept at three timeout values for twelve seconds each. Recovery stalls after a single rising edge remain dry; repeated long startup/output-pulse frames cannot reconnect a frozen heartbeat. A bypassed-first-stage mutation demonstrates premature permission before monitoring, and broken-clear/clock mutations exercise fault clearance and qualification. The frame model assumes valid pulse widths and settled supplies/calibration, and does not prove analog or propagation behavior.

All 16 Release CTest suites pass, with the final two bypass suites rerun after adding MPN fields. The current ARM source/object/artifact check remains passing. The current generated SVG was inspected through a raster rendering of its primitives, including the expanded 14-pin U24 symbol and added timing capacitors. The sheet now has 29 physical components plus two virtual power flags. Native KiCad remains unavailable: there is no local CLI, Docker's daemon is stopped, shell DNS failed and the Safari download action returned `cgWindowNotFound` without saving a KiCad image. No native import/ERC/render or installed software is claimed. Remaining work includes the relay driver, analog circuits/power/mute, PCB, mechanical fit and real-board qualification.

NZ sourcing records now include indexed overseas-stock listings through NZ storefronts for the selected watchdog and dual flip-flop. Counts/prices are observations that must be reconfirmed at purchase; local warehouse stock is not established. The Seed remains a NZ pre-order, and no parts were ordered.


## Integrated carrier native checks, 22 October 2026

The A0.2 electrical draft adds eight circuit sheets alongside the permission
sheet: relay drivers/input mute/delayed reconnect, line audio/gain modes, analog
and digital power, analog/reference health, switches, pot muxes, LED chain, and
Seed/SD/touch/USB wiring. The consolidated BOM contains 470 physical components.
Thirteen host circuit tests read emitted CAD pins/wires/labels and check scan
positions, physical module pads, harness order, NC dry paths, driver polarity,
power polarity, and ideal gain/rail budgets. They do not simulate analog dynamics.

Earlier statements that no local KiCad CLI existed are superseded. A pre-existing
signed KiCad 10.0.7 bundle was found under `/private/tmp/rmx-kicad`. The integrated
`hardware/electrical/carrier.kicad_pro` / `.kicad_sch` now opens nine child sheets
with global harness nets and local internal nets. A generated RMX symbol library
and project symbol/footprint tables resolve the cached symbols. Initial native
checks found missing library configuration, unverified cross-sheet supplies, an
internally parallel LDO pad modeled as two power drivers, and unannotated jack/
socket references. Those issues were corrected; no custom ERC exclusions or
error suppression were added. Two standalone bypass power flags are omitted in
the integrated project so actual carrier sources drive its power nets.

The final native ERC reports zero violations across ten pages. Native XML netlist
export completes without warnings and matches every physical component/value/
assigned footprint and all 1,486 connected physical pins, including cross-sheet
nets and explicit NC handling. All 333 assigned footprints have matching
pad-number sets in the bundled KiCad libraries. **137 physical parts still lack
footprints**, and pad-number agreement does not validate manufacturer geometry,
orientation, rated operation or physical fit. Ten native pages were plotted and
visually inspected for overall placement; detailed manufacturer-symbol/footprint
review remains open. The source-hashed `hardware/electrical/native-check.json`
records native tool identity, source hashes, report/export hashes, default ignored
ERC checks and footprint-library hashes. `tools/check_carrier.py --check` rejects
stale source evidence without requiring KiCad; regenerating evidence requires
native KiCad and the footprint libraries.

All 19 Release CTest entries pass, including the new current-source native-record
check. The ARM firmware source/object/artifact record remains current; no firmware
behavior changed in this carrier work. No board has been fabricated or flashed,
and no physical audio, callback deadline, fault-to-dry, thermal or reference-sound
measurements were performed. Input protection, mono normalling, part/footprint
completion, PCB layout/DRC, rear-panel reconciliation, enclosure interference and
physical commissioning remain required. A pre-existing OpenSCAD bundle was also
located, but has not been used to validate the solids. No browser download block
was overridden. No parts have been ordered.


## B1 budget hardware implementation, 23 October 2026

The active [B1 variant](../hardware/budget/README.md) implements the 5 V,
consumer-level redesign while retaining the existing Seed engine, control scan,
SD sample/User loading and heartbeat permission circuit. A0.2 remains separately
available. B1 includes AC-coupled stereo input/output, TLV9064 gain recovery and
unity trimmers, a single normally-dry stereo relay, midrail health supervision,
fused switched USB power and lower-current LED resistors. Native ERC found and
helped correct an orphan manual-bypass header net; a regression now verifies its
connection to the actual MANUAL_N reset input.

KiCad 10.0.7 reports zero ERC violations across nine pages. The exported netlist
matches all 423 physical components and 1,312 connected pins. Assigned footprint
pad-number sets match the bundled libraries; this does not establish manufacturer
geometry or physical fit. The 100 x 100 mm four-layer carrier contains 106 circuit
footprints plus four mounting holes. Its saved values, footprints and pad nets
match the carrier circuit subset. Native DRC reports zero violations and zero
unconnected items, with no custom exclusions. Gerbers and drill files are exported
as an engineering-review draft with source/output hashes; nothing was ordered.
The Seed, controls, LEDs, touch strip and SD module remain wired assemblies.

The split panel, joiner and shaft coupon STL meshes pass planar coverage, positive
volume and two-faces-per-edge checks. Their panel drawing and a native PCB top/
fabrication plot were visually inspected. Full tray, knobs, buttons and lever
SCAD solids remain unrendered: the available OpenSCAD bundle fails signature
verification and was not executed. Purchased-part dimensions, lever mechanics,
underside interference, tolerances and a physical fit print remain open.

Firmware adds bounded, atomic boot-time RMX/CALIB.TXT parsing, endpoint/inversion/
center calibration and a 2,400-frame stereo startup fade. DSP-ready waits for 38
complete 64-frame callbacks. Calibration tests cover malformed and fragmented
files, failure rollback, control mapping and fade timing; the standalone test also
passes AddressSanitizer/UndefinedBehaviorSanitizer. All 26 current Release CTest
entries pass. The ARM build and current-source artifact check pass: QSPI 495,964
bytes, AXI SRAM 48,472 bytes, DMA-region 18,204 bytes, backup SRAM 12 bytes and
SDRAM 62,914,560 bytes. No flashing or real callback timing measurement is claimed.

The cost ledger totals NZ$295.77 with only NZ$4.23 remaining, assuming free
printing, DIY assembly, reused USB power/cables and consolidated delivery. Many
rows are allowances and the NZ Seed price is a pre-order; this is not a confirmed
delivered basket. No revision/replacement reserve is secured. Real rail/current/
thermal/SD/USB checks, audio/noise/headroom measurements, fault-to-dry timing,
startup/dropout tests and reference-unit comparisons remain required. B1 does not
add USB audio/MIDI or complete original SD/RSD compatibility, lighting feedback
or exact original effect behavior.

## Measured DSP checkpoint: 26 October 2026

The original RMX-1000 Plug-in 2.2.0 is now captured through its public VST2 interface. The [measurement workflow](audio-matching.md) and [research records](../research/audio/measurements/) define the exact settings, hashes and exclusions.

- A clean snapshot of `5f1887f` plus the audio changes passes all 31 CTest groups. The latest shared-worktree run separately encountered failures in the ongoing rail-disconnect/thermal electronics fixtures; those uncommitted hardware changes are outside this audio checkpoint.
- Eight offline-host regressions pass for each current project AU and VST3, including event timing, parameter readback logs, state preservation and Auto/manual tempo selection. The project VST3 smoke probe passes 359 checks across 153 project parameters.
- Thirty-five static Isolator cases and fifty static Echo cases across 120/137 BPM pass the declared per-channel waveform criterion. The worst errors are approximately 0.0014% and 0.017%; isolated Echo returns also pass. These are scoped error ratios, not percentages of perceived similarity.
- Four default-Noise positions excluded from coefficient fitting pass 600-second per-channel band/level statistical screens. The original random generator is not reproduced.
- Integer/fractional tempo impulses and Noise tails confirm whole-millisecond beat periods before subdivision. Auto off holds manual tempo in the plug-in; Auto on follows the host.

Native app/AU/VST3 builds succeed. Desktop timing remains below the benchmark budget. Original hardware, other sample rates, overload, modulation/resonance, remaining effects, factory sampler matching, Release and combined gestures remain unverified; this is not full-device 99% conformance or an embedded deadline result.

## Filter Echo checkpoint: 26 October 2026

Static factory BPF/HPF/LPF Echo at 48 kHz, Normal width and Sub2 zero now pass 164 original-plug-in comparisons. The suite includes direct impulse windows, separate echo tails, six fresh stereo Main positions per effect and four crossfaded Sub1 positions per effect at 137 BPM. Maximum checked per-channel RMS errors are approximately 0.0018%, 0.0063% and 0.16%, respectively. Nine native VST3 captures also pass, including button-off tails. Exact settings, reference/candidate hashes and per-case results are in the [filter validation record](../research/audio/measurements/2026-10-26-filter-validation-48k.json).

A real Git clone of `6488916` plus the owned audio source/test overlay passes all 31 CTest groups in 43.63 seconds. The clone excludes unrelated ongoing hardware edits. New regressions check measured direct/tap values, tails after button-off, stereo isolation and finite output across all 256 raw positions. Native app, AU and VST3 builds pass; eight offline-host regressions pass for each AU/VST3, and the VST3 smoke probe passes 359 checks across 153 parameters.

The bounded-arena check reports 29,025,584 bytes for engine buffers, 35,649,584 with project factory samples, and 54,926,384 with 64 seconds of stereo bank storage. Replacement peaks at 55,099,184 bytes inside the 62,914,536-byte usable arena; audio processing allocates no arena storage. The desktop 2,000-block/configuration benchmark passes its 50% threshold, with worst p99 12.0782% during concurrent build/capture activity. This does not establish Cortex-M7 timing or hardware sound matching. Remaining effects, advanced profiles, changing controls, sampler, Release, overload and other host rates still require measured work.

## Crush checkpoint: 26 October 2026

Factory Normal-width Crush at 48 kHz with Sub2 zero now passes 54 static comparisons, including independent stereo probes, separate tails, 90/128/137 BPM, and seven early/late clock-boundary impulses. Worst checked per-channel RMS error is approximately 0.021%. Eight native VST3 cases pass, including the previously troublesome clock positions and button-off tails. Five seconds of direct-only noise at each of four boundary positions verifies the sample-hold arithmetic against observed events. The [identification](../research/audio/measurements/2026-10-26-crush-identification.json) and [validation](../research/audio/measurements/2026-10-26-crush-validation-48k.json) preserve the exact scope and hashes.

A clean Git clone of `5f8be41` plus the owned audio overlay passes all 31 CTest groups in 47.15 seconds. New regressions cover original late impulses, all raw Crush positions and matching settled output when controls are restored before versus after preparation. Native app, AU and VST3 builds pass; each AU/VST3 host suite passes eight regressions, and the VST3 smoke probe passes all 359 checks across 153 parameters. Three fresh BPF/HPF/LPF renders remain bit-exact with the preceding checkpoint.

The bounded-arena figures remain 29,025,584 bytes for engine buffers and 55,099,184 replacement-peak bytes, with no callback allocations. The 2,000-block/configuration desktop benchmark has worst p99 1.48279% of the 128-frame/48 kHz deadline. This remains a host measurement. Original first-host-block startup, moving controls, advanced profiles, remaining effects, sampler/Release behavior, physical hardware and other sample rates remain unverified.

## Spiral research and return-component checkpoint: 26 October 2026

A 192-capture campaign now records original factory Spiral Up/Down at 48 kHz. The analyzer retains diagnostics and provenance from 106 selected captures; all 192 generated input/control recipes reproduce the recorded fixtures exactly. The [identification record](../research/audio/measurements/2026-10-26-spiral-identification.json) documents non-additivity, channel coupling, tone-level scaling, latency and pitch diagnostics. The pitch generator remains unmatched.

The extracted `FactoryEchoReturn` component passes 32 comparisons using the original pitch stream as input, including independent stereo probes at Main 113 and 120/137 BPM. Worst checked per-channel RMS error is 0.000047%. This validates only the outer return, not a clone pitch generator or full Spiral effect. Four complete BPF/HPF/LPF/Crush renders are bit-identical to the preceding checkpoint. See the [component record](../research/audio/measurements/2026-10-26-spiral-return-validation-48k.json).

An isolated local clone of `9bbe683` plus the owned audio overlay passes 30 CTest groups in 32.33 seconds. The electronics tooling group was run separately: its first 180-second batch passed 185 cases before the time limit; a continuation ran only the remaining 68, all passing. Together all 253 electronics cases pass. The earlier archive-based full-suite attempt was stopped in favor of the actual Git clone; it is not counted as a complete pass. Unrelated ongoing hardware changes are excluded from the clone and this commit.

Native app, AU and VST3 builds succeed. Eight offline-host regressions pass for each AU/VST3, and the VST3 smoke probe passes across 153 project parameters. New component regressions cover measured return gain, crossfaded taps, 0.75 repeats, channel isolation and retained tails at 120/128/137 BPM. Engine-buffer and replacement-peak allocation remain 29,025,584 and 55,099,184 bytes with no callback arena allocation. No new embedded timing or hardware-equivalence claim is made. Full Spiral, Reverb, advanced profiles, gestures, sampler/Release, overload and other sample rates remain outstanding.

## Spiral core research checkpoint: 26 October 2026

The [core research record](../research/audio/spiral-core.md) adds 94 verified capture recipes. The locked NumPy-only identifier checks reference provenance and analyzes 42 selected recordings. Joint quiet/clipped first-pass fits have normalized RMS errors below 0.00003%; first quiet-return fits are below 0.00005%. These are component identification windows, not held-out complete-effect passes.

The standalone experimental C++ candidate compiles with `-Wall -Wextra -Wpedantic`. Four complete mono/square cases pass the one-percent whole/wet per-channel screen, with largest checked wet error about 0.017%. Six complete sparse, stereo broadband and DC-conditioned cases fail, and the comparison CLI correctly returns exit code 1. The [full report](../research/audio/measurements/2026-10-26-spiral-core-prototype-48k.json) retains both results. The failed candidate remains outside the production engine.

Capture verification confirms exact input samples, controls, BPM, tail, host block size and receipt/input/output/plan hashes for all 94 recipes. Numerical fitting and Python compilation succeed. Negative checks reject unreviewed calibration, invalid direction/time/tail arguments and an existing output without overwriting it. This checkpoint changes research tooling and evidence; it adds no production audio-path change or full-device fidelity claim.
