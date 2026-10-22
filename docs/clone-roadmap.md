# Complete RMX-1000 replication: requirements and evidence

The objective is full functional and sonic replication, with a standalone hardware implementation. The current changes are progress toward that objective, not a redefinition of completion as an inspired effect, a desktop-only tool or an unbuilt enclosure. A checked item below is limited to the stated evidence. The physical reference is the RMX-1000 with firmware 2.20; its operating manual, firmware MIDI addendum and remixbox manual define behavior. Reference captures remain necessary for undocumented curves and sound.

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
- [ ] Complete the original sampler editing/preview workflow and SD integration. Native/plugin playback editors and preset loop/BPM recall are implemented. Shared bank validation and PCM decoding now support boot-time FatFS SD loading, plus a desktop sample-card exporter. Host roundtrips and bank rollback/memory tests pass; physical card I/O remains unverified.
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
- [ ] Flash real hardware; verify SDRAM/cache, callback deadlines, stack high-water and boot/error behavior.
- [ ] Complete SD effect presets/RSD interoperability, nonvolatile calibration and USB MIDI; finish lighting/error feedback. Sample-bank loading now cross-builds with FatFS, bounded bank replacement and card error status, but has not run on a board.
- [ ] Electrical CAD: complete line-level/power/control/watchdog/relay schematic, named parts, footprints, ERC and reviewed netlist.
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
