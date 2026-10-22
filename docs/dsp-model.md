# DSP behavior and remaining matching work

The engine now has separate portable Scene and Isolate processors. Both use bounded PMR audio storage and receive smoothed performance controls. The algorithms implement the documented signal functions; their numerical curves, rhythms and sound are project implementations pending comparison with an original RMX-1000. Passing these tests does not establish sonic equivalence.

The source references are Pioneer's [operating manual, effect types on pages 15–17](https://manualzz.com/doc/79710635/pioneer-rmx-1000-dj-effector-owner-s-manual) and [remixbox manual, parameter ranges on pages 12–14](https://manualzz.com/doc/58880568/pioneer-rmx-1000-remix-station-owner-s-manual). The linked pages are mirrors of the manufacturer-authored manuals.

## Isolate

`include/rmx/Isolator.h` / `src/core/Isolator.cpp` own the state for each selected audio bus. The complementary crossover remains a first-order project implementation so all three neutral bands sum transparently. Matching the hardware's crossover slopes/phase still requires measurement.

- **Isolator:** individual per-band minimum choices of −6, −12, −18 dB or full kill; maximum choices of 0, +3, +6 or +9 dB. Current defaults are full kill / +6 dB. Finite ranges interpolate in dB; full kill uses a smooth amplitude curve. These defaults and intermediate knob curves are not claimed as measured factory calibration.
- **Cut:** a filtered bass/transient detector estimates the kick component. LOW reduces that detected component; MID high-passes the remaining signal; HI low-passes it. MID/HI filter resonance and kick-reduction strength are independently configurable. The detector currently uses a 180 Hz low-pass, 1 ms attack, 25 ms fast-envelope release, 250 ms baseline, 120 ms retrigger exclusion and 90 ms decay. These are tunable project values, not extracted hardware constants. Simultaneous instruments can overlap the detected component.
- **Add:** clockwise controls add delayed audio from their respective original bands. Each band has its own User pattern. The current Pattern 1 taps are 1/8, 1/4, 1/2 and 1 beat; Pattern 2 is 1/8, 3/8, 5/8 and 7/8; Pattern 3 is 1/4, 1/2, 3/4 and 1. Gains decay across taps. These tap patterns have not yet been matched to the three original pattern choices.
- **Trans:** counterclockwise position selects a musical rate and cut depth. The phase follows the performance beat, including Nudge. A short edge slew avoids discontinuous gate transitions. Three per-band rate maps are available; the original maps/waveforms remain unmeasured.
- **Roll:** clockwise engagement records a forward band window and repeats it. Window length follows the per-band beat map. It does not repeatedly recapture the preceding history. Changes to rate restart acquisition; matching the original's change-of-rate/capture-boundary behavior remains outstanding.
- **Gate:** uses a linked stereo band envelope with separate gain attack/release rather than gating at individual waveform zero crossings. Each band has Mild/Default/Wild depth.
- **Drive:** per-band saturation and depth, with level compensation. The original transfer function/oversampling and aliasing behavior remain unmeasured.

## Scene performance controls

The parameter IDs `scene_depth`, `scene_time`, and `scene_resonance` remain stable. Their displayed meanings are now Main, Sub1 and Sub2. Sub1 retains its old numerical 0–7 range for preset/host compatibility, but is continuous for Noise/reverb level changes. Tempo effects select one of four Sub1 regions. BPF Echo, Echo, Spiral Up/Down, HPF/LPF Echo and Crush Echo each store four independent User divisions. Choices run from 1/16 through 2 beats; Echo additionally permits 4 and 8 beats. Noise and reverb keep continuous Sub1 level controls. Noise uses a fixed one-beat internal echo, so its volume knob no longer changes echo time. That fixed time remains provisional.

| Effect | Main | Sub1 | Sub2 |
| --- | --- | --- | --- |
| BPF Echo | Band-pass cutoff | Echo division | Output modulation or filter resonance |
| Echo | Dry/echo balance | Echo division | Output filter cutoff |
| Noise | Generated-noise filter cutoff | Generated-noise level | Modulation or resonance |
| Spiral Up | Spiral delay-window length | Feedback echo division | Upward pitch amount |
| Reverb Up | Reverb amount, additive dry path | Reverb level | High-pass output cutoff |
| HPF Echo | High-pass cutoff | Echo division | Output modulation or resonance |
| LPF Echo | Low-pass cutoff | Echo division | Output modulation or resonance |
| Crush Echo | Bit reduction | Echo division | Output modulation |
| Spiral Down | Spiral delay-window length | Feedback echo division | Downward pitch amount |
| Reverb Down | Transition from dry to reverb | Reverb level | Low-pass output cutoff |

These replace the former generic Sub2-to-feedback mapping. Echo repeat feedback is now independent of Sub2. Feedback character is stored separately for each applicable effect. Echo has filter width and Hold/DJM settings; the earlier filter-type option remains a project extension, rather than a claim that remixbox exposes that option. Hold/DJM controls the feedback mode; Hold freezes the circulating delay when Main reaches its full end.

The four regions currently cover equal quarters of normalized knob travel, with provisional default divisions of 1/8, 1/4, 1/2 and 1 beat. The original boundaries, hysteresis and per-effect factory assignments still need measurement; old `scene_time` positions now follow this four-region map rather than the previous eight-step approximation. Echo's longest setting is exercised at 40 BPM, producing a measured 12-second delay.

BPF/HPF/LPF/Noise have separately saved modulation-versus-resonance modes, waveforms and resonance character. Supported waveforms are triangle, saw, square, deterministic sample-and-hold random, and side-chain. The current modulation acts on output amplitude; the exact original modulation circuit, rate/depth maps and side-chain behavior must be measured before sonic matching can be claimed. Filter width and Noise min/max level choices are stored independently. The old global Noise Color is retained as a project-specific tilt option; 0.5 leaves the generated noise untilted.

Spiral uses a two-head, crossfaded delay pitch shifter inside the echo feedback path. Sub2 controls pitch independently of Main's window length, with Linear/Key variation and a configurable window span per direction. The current maximum shift is an octave. The original pitch range, head windows, feedback filtering and trajectories remain unmeasured.

Reverb uses an eight-line Householder feedback matrix with damping, two room sizes and three decay-time choices per direction. Feedback gains are derived from the chosen decay time rather than from Sub2. Each direction now has a separate low-pass/band-pass/high-pass User choice. The defaults are high-pass for Up and low-pass for Down; Sub2 moves the cutoff in the direction documented above. Original diffusion, early reflections, stereo field, pitch behavior, room sizes and decay maps still require a reference comparison.

## Sampler playback

`SamplePlayback` stores One-shot/Loop and original sample BPM independently of Default/User advanced effects. Loop mode is accepted only for slot 1 of each bank, with BPM 70–200, following the remixbox sampler editor. A pad press starts/stops a loop; strip/sequence starts reuse its voice without toggling it off. The engine wraps fractional reads safely and interpolates across the last/first frames. One-shot playback includes the last frame, including one-frame assets. Pitch and sample-rate conversion apply to both playback modes; loop speed also follows performance BPM divided by original BPM. An allocation-free stereo overlap-add reader now separates loop tempo from pitch; neutral playback retains direct interpolation. See [sample stretching](sample-stretching.md) for synthetic checks and transient/aliasing limits. Original loop time-stretch, timing, voice limits and choking still need reference measurement.

`SampleBank` contains four internal drum assets separately from its sixteen bank slots. Internal sources are always one-shots; SD replacement changes only bank slots. `sample_source` selects internal drums or bank samples independently of the live-input roll selector. Queued/host hits capture their source and bank; overdub stores that identity plus explicit loop-stop events. Changing the current selection therefore does not redirect existing voices or recorded hits. Firmware boots with the four synthesized internal drums and empty sample banks; desktop factory banks retain the project's sixteen synthesized variants. Original factory recordings are not supplied.

Presets persist `sample_mode` records alongside WAV references. Older presets default to One-shot/120 BPM and bank playback; new presets store source selection. Native and plugin import/preset paths validate the shared 16-second per-bank storage limit before installing assets. General WAV decoding remains available at 8–192 kHz. A separate strict PCM reader and `rmx_card_export` prepare/load 48 kHz sample banks using the project card layout; original RSD/SD interoperability remains unfinished. The native trim editor adds Loop/BPM, and the plugin adds a playback dialog. Native editing writes a managed WAV; metadata remains in the preset/session. Preview, card-availability feedback and the complete original sampler workflow remain unfinished.

`rmx_sampler_tests` covers separate internal/bank playback, queued and sample-offset source capture, mixed-source overdubs, loop start/stop replay, four-bank looping, one-shots/final frames, short buffers with large fractional steps, host BPM/pitch/rate conversion, Panic, metadata roundtrips/legacy source defaults, invalid slots/BPM and the exact 16-second bank boundary. Bounded-arena and global-allocation checks run active sampler loops alongside the existing effects and input roll. These checks do not establish hardware sonic matching or DAW certification.

The eight X-Pad positions now have separate User beat assignments. The sixteen choices follow the remixbox X-Pad table on page 14, including 1/24, 1/12, 1/6, 1/3, 2/3 and 3/2 beats. Default uses the previous project layout, retaining saved User choices. Sample repeats and new live-input captures resolve the same layout; desktop strip labels show those effective values. The preallocated capture is twelve seconds, covering eight beats at 40 BPM. Timing uses double-precision beat divisions and rounds capture duration to the nearest frame. `rmx_xpad_tests` measures all sixteen repeat intervals, quantized host-grid triplets, embedded touch assignments, Default/User restoration, legacy preset positions and full-length capture/replay. Held live-roll division/pitch changes, Slip/Divide modes and gesture overdub remain unfinished; the default layout and phase behavior still require reference-unit comparison.

## User settings and compatibility

`ParameterInfo::advanced` identifies custom settings. Default uses their factory defaults in DSP while retaining the saved User values; selecting User restores them. Native settings now scroll through the full set with named choices, and plugin parameters expose those choices to hosts. Old presets receive defaults for missing fields. SceneTime fractions roundtrip without being rounded to integers. DSP behavior intentionally changes where the former mapping contradicted the reference functions; older presets are not guaranteed to sound identical to the previous approximate algorithms.

The parameter model does not yet cover the entire remixbox schema. Independent crossover settings for each isolate mode, echo application-range settings, sample/oscillator settings, all release-lever ranges, effect locks/button sensitivity and RSD/SD conversion remain required.

## Verification

`rmx_isolator_tests` checks neutral stereo for every mode, all gain endpoints, additive eighth-note timing, kick reduction versus sustained bass, residual high/low-pass behavior, Trans rate changes, forward band capture, absence of waveform-cycle gate chopping and state roundtrips.

`rmx_scene_tests` checks neutral Main, Noise volume/filter/side-chain behavior, Echo onset and unchanged feedback across Sub2 extremes, channel isolation, HPF/LPF action, resonance None, room-size reflection timing, reverb control roles, Spiral pitch direction/amount, four-region assignments at every Echo division and the slowest supported BPM, Default/User restoration through the engine, Echo filter width, all three reverb filter choices, and fractional/per-effect state roundtrips. These are functional signal measurements, not reference-unit golden files.

`rmx_memory_budget` runs every Scene/Isolate combination and live roll against a real bounded allocation resource. `rmx_benchmark` now covers all 40 Scene/Isolate combinations with positive and negative knob settings. Both are host checks. Cortex-M7 timing, converter measurements, musical listening fixtures and original-unit matching remain unverified.

All delay lines share `FractionalDelay`. Integer index wrapping avoids a floating-point boundary that could round a read position to one past the buffer end. Regression coverage includes one-ULP positions around wrap/region boundaries, interpolation over multiple wraps, reset and nonfinite ages. AddressSanitizer/UndefinedBehaviorSanitizer checks cover the full core suites.

SD loading is a pre-audio operation. Each bank is replaced atomically, including empty slots, with one bank of temporary PMR storage. The same decoder is exercised by memory-file tests and exporter roundtrips; the FatFS adapter uses an AXI SRAM bounce buffer. Hardware cache/card/boot tests remain unverified. See the SD layout and preparation instructions in [hardware/README.md](../hardware/README.md).
