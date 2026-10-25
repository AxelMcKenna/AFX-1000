# Complete RMX-1000 replication: requirements and evidence

The objective is full functional and sonic replication, with a standalone hardware implementation. The current changes are progress toward that objective, not a redefinition of completion as an inspired effect, a desktop-only tool or an unbuilt enclosure. A checked item below is limited to the stated evidence. The physical reference is the RMX-1000 with firmware 2.20; its operating manual, firmware MIDI addendum and remixbox manual define behavior. Reference captures remain necessary for undocumented curves and sound.

## Implementation update: 22 October 2026

- [x] Improve AUTO pulse-phase tracking, gradual clock correction, silence invalidation and tempo-change recovery. Synthetic fixtures pass; real-music and reference-unit validation remain open.
- [x] Share MIDI clock handling across native and plugin adapters, including Start/Stop/Continue and Song Position Pointer. Plugin clock/transport events use sample offsets with DAW transport priority.
- [x] Separate loop tempo from pitch using bounded, stereo-linked overlap-add. Neutral playback retains direct interpolation. Reference-unit sound and transient behavior remain unverified.
- [x] Add an optional Ableton Link adapter and native setup control. The SDK-free build passes; Link remains disabled in packaged builds, and enabled compilation/live peers still need validation.
- [x] Replace the hardware photograph with original amber/teal panel artwork in native and plugin builds.
- [x] Add reference-audio capture/comparison tools, a persistent offline stress tool, a VST3 runtime probe and universal Mac packaging with source/dependency archives, notices and hashes.

The verified source snapshot is commit `f87aaad009eb8d03035f21431c95341a5c587727`. Release and ASan/UBSan runs each passed all 14 CTest entries. The VST3 probe passed 329 checks, covering 138 project parameters and 4624 processed blocks. Universal native/AU/VST3 builds and the firmware cross-build passed. These results apply to that snapshot; later workspace changes need their own validation.

The offline stress run processed 7200 simulated seconds with no non-finite output or dropped events, but recorded three callbacks over their frame deadlines. It does not satisfy the physical two-hour live-soak requirement. Packages are ad hoc signed and not notarized. Four logical commits were exported; GitHub push failed because the session could not resolve `github.com`.

- [ ] Compare against real RMX recordings and complete loudness-matched listening checks before claiming sonic parity.
- [ ] Validate FLX4/FLX6 routing, actual DAW operation, device recovery and a real two-hour session.
- [ ] Verify AU runtime. The component built, but process-local registration returned null during the probe; the cause is undetermined.
- [ ] Build and exercise the Link-enabled configuration with the separately supplied SDK.
- [ ] Flash and validate physical hardware, including audio, controls, storage and fault recovery.
- [x] Add the proprietary project rights notice; retain third-party terms separately. Commercial permission for combined JUCE/Link distribution and legal review remain separate requirements.

See the [engineering report](engineering-update-2026-10-22.md) for measurements and limitations, plus [synchronization](synchronization.md), [sample stretching](sample-stretching.md), [reference validation](reference-validation.md) and [release packaging](release.md).

## Performance state and timing

- [x] Pad one-shots remain immediate with Quantize on; sample-offset event path is retained. Regression-tested.
- [x] Four-beat overdub starts relative to the first hit and retains recorded bank identity; Overdub off stops/deletes. Regression-tested.
- [x] Independent pad-lane mute/delete and physical button chords; desktop Shift/Alt equivalents. Regression-tested.
- [x] Quantized roll starts and continuous Nudge timing offset without changing the base BPM. Regression-tested; 2% nudge speed is provisional until measured.
- [x] Tap averaging and long-interval rejection. Implementation present; further jitter/tempo-change fixtures required.
- [x] Live roll captures from the touch rather than from historical pre-touch audio; fixed capture repeats, X-level blends dry/roll, and release fades. Regression-tested.
- [ ] Match roll capture/phase behavior when dragging through beat divisions and changing pitch during acquisition; verify original hold behavior.
- [ ] Record/replay/mute/delete X-Pad strip transformations of the overdub loop, with the original interaction between Roll and recorded sample lanes.
- [x] Separate four internal drum assets from the four sample banks; preserve source/bank on queued hits and overdubs; support loop-pad start/stop and Hold+pad silent selection. Covered by host signal/control regressions; internal drums remain synthesized substitutes.
- [ ] Match original voice limits/choking, bank availability/LED/chord details and time-stretch. Per-slot loop/BPM metadata, slot-1 restrictions, looping playback, tempo/pitch conversion and same-loop voice reuse are implemented; original-unit timing and sound comparisons remain required.
- [ ] Validate the implemented audio beat-phase estimator on arbitrary music and against the reference. Synthetic phase, silence and tempo-change fixtures pass; half/double-time ambiguity and musical downbeat interpretation remain open. See synchronization.md.
- [ ] Verify Nudge/Tap/Auto chord details, clock start/continue/stop, seek and host-loop behavior against a physical unit.

## DSP and routing

- [x] Implement the first [drum and Noise sound revision](dsp-model.md#sound-revision-23-october-2026): new drum sources and per-drum envelopes, asymmetric pitch endpoints, filtered one-shot downsampling, a shaped Noise sweep/echo and linked output protection. Separate builds and offline auditions are prepared. Reference sound matching, regression coverage and target CPU/deadline measurements remain open.
- [x] FX SOURCE bypasses Release for unselected signals; Noise does not depend on source buttons. Regression-tested.
- [x] User-configurable retention of Scene/Isolate/X-Pad after Release, exposed to native settings and plugin parameters. Regression-tested.
- [x] Implement Cut/Add kick detection, residual filtering and additive band delays. Signal tests pass; detector constants and named tap patterns still require reference-unit matching.
- [ ] Match Trans/Roll rate maps, quantized phase, capture timing and user patterns; match Gate/Drive envelopes and depth curves.
- [ ] Match isolator crossover topology, slopes and gain maps, including all remixbox min/max/crossover options.
- [x] Implement the documented main/Sub1/Sub2 signal roles for all ten Scene FX. Signal tests cover cutoff, level, pitch, feedback independence and reverb direction. Separate four-region assignments, Echo filter width and reverb filter types are implemented. Exact control curves, factory assignments, region boundaries and sound remain unverified.
- [ ] Implement configurable modulation/resonance types, waveforms, sidechain behavior, filter widths/types, feedback modes, spiral pitch maps and reverb controls.
- [ ] Match Back Spin, Echo and Vinyl Brake trajectories, lever ranges and feedback behavior; preserve configurable section retention.
- [ ] Verify effect ordering, tails during source changes, gain staging and bypass/release transitions with combined sections.
- [ ] Match factory samples through recorded/licensed assets or measured synthesis. Current samples are project-owned substitutes.

## Assets, presets, MIDI and host adapters

- [ ] Finish the complete User schema, including sample/per-lever settings, echo application ranges and per-mode crossover assignments. Per-band isolator ranges/patterns/depth and per-effect four-region delay choices and many other separate Scene choices are implemented with stable IDs and old-preset defaults; the complete schema is still unfinished.
- [x] Eight User-assignable X-Pad positions with all sixteen documented beat choices, including triplets; Default/User recall and physical touch mapping. Signal-tested. Capture accommodates eight beats at 40 BPM without truncation.
- [ ] Roll/Slip Roll/Divide Roll, drum gain/decay/envelope and asymmetric pitch ranges; match held-gesture phase and pitch behavior to the original.
- [ ] Complete the original sampler editing/preview workflow and SD integration. Native/plugin playback editors and preset loop/BPM recall are implemented. Boot-time FatFS loading and the desktop card exporter now transfer sample banks and the currently implemented User settings. Host roundtrips and rollback/memory tests pass; physical card I/O and original SD/RSD compatibility remain unverified.
- [ ] RSD/SD import/export interoperability or a verified conversion tool. Current `.rmx` presets are a separate format.
- [ ] Full original-controller MIDI mappings, firmware addendum modes, channel handling and controller/LED feedback.
- [ ] DAW automation of performance gestures, sample/pattern state recall and multiple-instance controller selection; validate AU/VST3 hosts and offline rendering.
- [ ] Plugin/native UI parity for all advanced settings and physical-control feedback, including mute/deletion indications.

## Embedded hardware and mechanical design

- [x] Portable fixed-capacity sequencer and button/analog/touch decoder with no GUI dependency. Host tests cover button chords, bounce rejection and touch release.
- [x] Audio/sample buffers can allocate from bounded external SDRAM. Actual host allocations fit at 48 kHz with all 64 seconds of hardware bank storage.
- [x] Initial Daisy firmware source, pin contract, 48 kHz/64-frame callback, controls/LED scan, touch driver and watchdog heartbeat/ready signals. Cross-built with the pinned Arm/libDaisy configuration; runtime behavior remains unverified.
- [x] A0 panel/enclosure source, DXF/SVG/PNG, coordinate table and preliminary BOM/wiring. Generator/2D clearance checks passed, preview inspected.
- [x] Pin the ARM toolchain/libDaisy and its submodules, cross-compile/link, inspect ARM ELF/map and verify source/artifact hashes and external arena placement. This does not prove runtime behavior.
- [x] Preserve C++ header dependencies during incremental ARM builds; reject missing/stale translation units and unlinked objects before recording firmware evidence. Host failure fixtures and actual Make header-change planning verified.
- [x] Export implemented User settings with stable IDs and load them before embedded audio starts, independently of sample banks. Bounded parsing, error rollback, physical-control preservation and Default/User audio switching are host-tested; actual card/board execution remains unverified.
- [ ] Flash real hardware; verify SDRAM/cache, callback deadlines, stack high-water and boot/error behavior.
- [ ] Complete original SD/RSD interoperability, nonvolatile User storage/calibration and USB MIDI; finish lighting/error feedback and live card insertion/loading. Boot-time sample banks and project User profiles cross-build with FatFS and independent error status, but have not run on a board.
- [ ] Electrical CAD: complete line-level/power/control/watchdog/relay schematic, named parts, footprints, ERC and reviewed netlist.
- [x] Extend the electrical draft with eight pin-connected carrier sheets: relay drivers/mute/reconnect, line gain modes, power, analog/reference health, buttons, pot muxes, LED chain and Seed/SD/touch/USB wiring. Added consolidated BOM/connection inventory and 13 host checks of emitted CAD and ideal budgets. This is engineering-draft evidence only; The integrated KiCad 10.0.7 project now passes native ERC with zero violations; its netlist matches 470 physical components and 1,486 connected pins. Pad numbers match the 333 assigned footprints; 137 parts still lack footprints. Part/footprint completion, input protection, mono normalling, PCB layout and physical qualification remain open. See [carrier design](../hardware/electrical/carrier.md).
- [x] Draft pin-connected watchdog/power-good/relay permission CAD with two-stage heartbeat recovery after faults and startup-frame handling. TPS3435 replaces the unsuitable TPS3431 and provides 49.995 ms nominal timing with explicit tolerance bounds. Generated schematic/BOM/SVG and tests of emitted connectivity and ideal fault/frame sequences; native import/ERC now passes in the integrated carrier. Complete carrier qualification and physical behavior remain unverified. See [electrical design](../hardware/electrical/README.md).
- [ ] Source the prototype through NZ suppliers with confirmed availability. [Sourcing record](../hardware/sourcing-nz.md) identifies the required 64 MB Seed at a NZ seller, currently pre-order/out of stock, plus overseas-stock watchdog/logic listings through NZ storefronts. Confirm stock, complete the remaining BOM and define/measure maximum complete fault-to-dry latency before freezing bypass parts.
- [ ] PCB layout, audio return paths, codec/input/output gain modes, original connector functions, protection, supply rails and analog output muting. No Gerbers exist yet.
- [ ] Physical reference measurement and final selected component dimensions. Add board mounting, connectors, lens retention, spring lever, inserts, strain relief and underside keepouts.
- [ ] Render/export the OpenSCAD solids, inspect assembly interference and print a fit model. Current solid source is unrendered.
- [ ] Assemble prototype; validate relay dry path on boot/crash/power loss, watchdog timeout, ADC settling, touch behavior, controls, audio levels, noise/THD and thermal/power budget.

Current DSP behavior, User choices, signal tests and unmeasured algorithm details are documented in [dsp-model.md](dsp-model.md).

## Completion evidence

- [ ] A reference corpus: dry/processed captures at fixed levels, BPM and control positions, with a manifest of unit/firmware, signal, routing and knob settings.
- [ ] Measured delay times/decay, filter responses, reverb decay/diffusion, pitch trajectories, sample pitch and release timing against reference. Define numerical acceptance tolerances from measurements rather than arbitrary "output changed" checks.
- [ ] Loudness-matched listening comparisons of real music and combined effects, including transition gestures.
- [ ] Physical round-trip latency, channel separation, headroom, response, noise and THD measurements meeting the published hardware specs.
- [ ] Two-hour full-control live soak, loss/recovery/fault tests, DAW host validation and target-platform build/runtime records.
- [ ] Review every requirement above against current artifacts and measured evidence before calling the clone complete.


## B1 budget hardware implementation, 23 October 2026

- [x] Implement a separate 5V consumer-level variant with TLV9064 input buffers/output recovery gain, input rail clamps, filtered/reference-qualified midrail, one stereo NC dry relay, preserved watchdog permission and lower-current LEDs. Native ERC/netlist evidence is source-hashed. The full RMX electrical specifications are not retained.
- [x] Place/route a 100x100mm four-layer audio/power/bypass carrier. Verify all 106 carrier component pad matrices and native DRC; Seed/panel assemblies remain wired offboard. Native records describe the checked scope and default ignored rules.
- [x] Add bounded SD control calibration with inverted endpoints/center mapping and transactional reads, plus a 50ms startup fade and delayed DSP-ready. Host failure/signal fixtures and an ARM cross-build verify implementation, not board execution.
- [x] Update rear ports, power switch/USB lead, carrier posts and split enclosure source. Export two panel halves, seam joiner and shaft coupon as checked closed flat meshes. Full tray/cap/lever solid export and assembled fit remain unverified.
- [x] Account for all circuit parts in a provisional NZ$295.77 cost ledger. It includes unquoted allowances, free printing, reused supply/cables and DIY assembly; only NZ$4.23 remains, with no revision reserve.
- [ ] Confirm a complete delivered supplier basket below NZ$300 and a 64MB SDRAM Seed delivery date; exact remaining offboard parts, dimensions and procurement remain open.
- [ ] Complete tray/controls/lever solid validation, purchased-part fit, analogue/thermal/fault/deadline/SD qualification, USB MIDI and reference RMX behavior/sound matching. No parts have been ordered and no prototype is assembled.

See [B1 build notes](../hardware/budget/README.md) for the actual files, build/check commands and limitations.
