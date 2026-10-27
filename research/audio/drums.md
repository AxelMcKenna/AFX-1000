# Factory drum sound matching

27 October 2026. The user has prioritized the factory **kick, snare, clap and hi-hat** ahead of the remaining effects. The current [`FactoryDrums.h`](../../include/rmx/FactoryDrums.h) generates project voicings; none of the four is yet reference-matched. The existing sampler tests verify behaviour, not resemblance to the original sounds.

## First reference campaign

The [24-case original characterization](measurements/2026-10-27-drum-original-characterization.json) uses RMX-1000 Plug-in 2.2.0, factory Default, stereo48k/120BPM, silent input, neutral pitch raw128 and level raw128. Each instrument has a baseline, fresh-instance repeat, callback32/callback256 repeats, a declared 37-frame trigger shift, and rapid retriggers. Baselines use callback128 and three separated hits. Original binaries and audio stay under ignored build artifacts; the report contains hashes and numeric observations.

[`rmx_drums.py`](../../tools/rmx_drums.py) checks exact plans, silent samples, callback/extent, receipt and auxiliary hashes, immediate/final parameter readbacks and the saved matrix before analysis. This is discovery, not a candidate holdout or a sound-match claim. No gain or alignment is fitted.

All four instruments are mono in the checked stereo outputs. Their three separated hits are bit-identical, as are fresh-instance and 32/128/256 callback repeats. Repeatability alone does not distinguish stored playback from deterministic synthesis.

| Instrument | First nonzero output after block-aligned trigger | Last nonzero delta, threshold1e-12 | Peak at raw128 level |
| --- | ---: | ---: | ---: |
| Kick | 48 frames | 25,567 frames | 0.707622 |
| Snare | 48 frames | 22,415 frames | 0.691373 |
| Clap | 32 frames | 60,655 frames | 0.602424 |
| Hi-hat | 48 frames | 14,290 frames | 0.727877 |

The declared 37-frame trigger shift moves the first output by 32 frames: onset delta becomes43 for kick/snare/hat and27 for clap. This exposes block/control timing, rather than just a freely shiftable sample waveform. Source changes and callback fragments must be modeled causally; an alignment search must not hide them.

The [first attempted retrigger models](measurements/2026-10-27-drum-retrigger-first-probe.json), using an original isolated hit as a component fixture, reject both unrestricted additive overlap and immediate single-voice restart under a naive floor32 event mapping. Relative errors exceed 100% for every instrument. This does not establish polyphony or a reset rule: partial-callback emission and trigger timing need to be accounted for before interpreting that result. It is not independent candidate sound validation.

## Reproduce and next work

```sh
uv run --locked python -m tools.rmx_drums capture \
  --host /path/to/Intel/RMXReferenceHost \
  --plugin /path/to/RMX-1000Plug-in.vst --session build/new-drum-session
uv run --locked python -m tools.rmx_drums analyze \
  --session build/new-drum-session --report build/new-drum-characterization.json
```

All destinations must be new. Next compare the actual Engine's existing drum output, quantify the kick's attack/body/decay mismatch, identify its pitch/envelope structure, and test revised hypotheses on new recordings. Pitch/level laws, alternate decay/envelope settings, rolls, overlapping instruments, retriggering and broader rates/profiles remain required. No drum accuracy percentage has been established.

## Existing synthesis baseline and first scalar observations

The [complete Engine baseline](measurements/2026-10-27-drum-existing-synthesis-baseline-48k.json) passes **0/24** cases under the declared 1% per-channel whole/attack/body/decay screens. For the four separated-hit baselines, whole-output relative RMS errors are approximately 124.3% kick, 105.2% snare, 126.4% clap and 110.4% hi-hat. These are waveform differences, not perceived-similarity scores. The report preserves the rejected baseline; there is no claim that the existing voicings match.

The [native fixture](../../tools/drum_probe.cpp) triggers the actual Engine with its current internal instruments, current normalized sampler-level mapping and neutral pitch. It has silent input and separately checks the predicted dry trace stays zero. Comparison uses the existing independently measured bypass convention, reference crop32/candidate crop0; it fits neither gain nor time shift. Trigger-phase differences remain visible. Build `rmx_drum_probe`, then run `uv run --locked python -m tools.rmx_drums compare --session SESSION --renderer RENDERER --output NEW_DIRECTORY`.

Read-only local inspection found separate original `rbnfx_kick`, `rbnfx_snare`, `rbnfx_clap` and `rbnfx_hihat` routines, oscillator helpers and named envelope arrays. The [numeric observation](measurements/2026-10-27-drum-scalar-observation.json) records those symbol names, array values, source/binary hashes and a kick-curve constant vector. No original instructions, executable or audio are committed. Repeatable hits alone had not established the generator type; these additional observations provide a concrete synthesis hypothesis to test.

The first two floats in the named kick triangle/EG/noise arrays are respectively about `(0.001,0.44)`, `(0.001,0.21514)` and `(0.001,0.15859)`. The clap's two arrays contain `(0.016,0.24)` and `(0.016,1.25)`; the hi-hat arrays contain `(0.002,0.30)` and `(0.002,0.23625)`. Their field semantics, update order and effect on complete audio are not validated just by reading values. A separately named kick low-cut coefficient vector is retained for filter identification. These are measured numeric facts, not manufacturer specifications.

[`rmx_drum_observe.py`](../../tools/rmx_drum_observe.py) reads only file-backed float constants from the reviewed local Intel binary, verifies its SHA-256 and Mach-O architecture, and records the symbol-inventory hash. Use `--binary ORIGINAL_BINARY --report NEW_REPORT` to reproduce. Raw local inspection output stays ignored. Next establish the kick's oscillator, pitch envelope, amplitude envelope, noise and filter update rules from independent observations, then freeze a candidate before further original captures. The current synthesis has not been changed on the basis of unvalidated constants.

## First independent kick candidate

The [research kick](experiments/KickResearch.cpp) passes [6/6 existing discovery programs](measurements/2026-10-27-kick-first-prototype-48k.json), including rapid retriggers and the shifted trigger. Whole-output relative RMS error is approximately **0.00790%**, with worst attack/body/decay window **0.01048%**, under the unchanged per-channel 1% criterion. This is development evidence; a different prospective set is still required. The live Engine still uses the original project voicing.

A [read-only scalar replay](measurements/2026-10-27-kick-scalar-replay.json) checks the original across 64 consecutive 16-sample subblocks. All three envelope trajectories and both oscillator phases replay exactly at their stated scope. The original render and its plan/audio/state/parameter-log/inventory files remain byte-identical with debugger observation. Phase replay uses observed frequency, so that component check is not an autonomous generator validation. The separate complete six-program renders supply that evidence.

The observed factory pitch-envelope decay is **0.343 seconds**, replacing the static file's initial 0.21514 value at runtime. Three linear envelope states advance in float32 once per 16 samples. Shaped pitch drives two float32 triangle phases, with frequency ratio0.6 and mix weights23/3. A shaped amplitude, moving bandpass, resettable XOR/add noise generator, small noise mix and measured low-cut filter complete the hypothesis. Retriggers fade the current voice over five 32-frame blocks before restarting; immediate restart and unrestricted overlap had failed. The model also generates the declared partial-callback FIFO timing, without fitting audio shifts or comparison gains.

This standalone fixture explicitly emits the measured nominal32 transport, so its comparison crops32/32; the earlier Engine baseline emitted candidate0 transport and used crops32/0. Both are declared timing conventions, not alignment searches. The hypothesis currently supports neutral raw128 level/pitch, factory kick and 48 kHz only. It contains no original audio recordings or calls into original DSP. The measured numeric calibration and local inspection informed the independently implemented hypothesis; raw original instructions and internal audio traces stay ignored.

Build `rmx_kick_research_probe`, then use [`rmx_kick.py`](../../tools/rmx_kick.py) with `--session`, `--renderer` and a new `--output` directory. [`rmx_kick_observations.py`](../../tools/rmx_kick_observations.py) verifies the separate normal/debugger captures and numeric trace before producing its component report. Freeze this candidate before different fresh trigger programs; other drums, full knob/settings coverage, Engine integration and full-device fidelity remain unfinished.
