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

All destinations must be new. The comparisons and kick hypothesis below establish progress at neutral factory controls. Pitch/level laws, alternate decay/envelope settings, rolls, overlapping instruments, broader rates/profiles and the other three generators remain required. No full-drum accuracy percentage has been established.

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

## First prospective failure: cold controls and output fade

After [freezing the first candidate](measurements/2026-10-27-kick-first-predictions.json), eight new trigger programs are captured at callbacks8/15/31/63/511/1024/2048/4096, including immediate startup and interrupted retriggers. The [first prediction fails](measurements/2026-10-27-kick-first-holdout.json): three programs pass, four fail waveform windows, and one fails the strict original-control contract before waveform scoring. No waveform gate is relaxed.

The original returns immediate readback0 for a KickButton=1 request at frame0, before its first processing callback. Later requests, including at frame1, read back as requested. The earlier discovery captures started after one second and had not exposed this distinction. The failed contract is preserved explicitly rather than accepting an unexplained readback discrepancy.

The four waveform failures occur during cold startup. Their complete-program RMS errors can be below 1% while short attack windows fail, up to about 46.4%. Original/candidate ratios in the early nonzero samples follow a **linear float32 ramp of 1/160 per generated sample**, using the internal sample index before partial-callback emission. Late sound remains close. This diagnoses a missing global output startup fade, separate from the three kick envelopes. Ratio inspection is diagnostic; no comparison gain is fitted or used for acceptance. The corrected hypothesis must be frozen before another different prospective set; these first eight then become regressions.

## Corrected startup: eight new prospective passes

The corrected generator ignores a trigger before its first nonempty process call and advances the global linear startup fade on every internally generated sample, including silent blocks. Applying this fade at the physical output index would give different answers with partial callbacks. Retriggers reset the voice, while this global fade continues from startup.

The [six discovery regressions](measurements/2026-10-27-kick-cold-discovery.json) and [eight former holdout regressions](measurements/2026-10-27-kick-cold-former-holdout.json) all pass. A [new frozen prediction](measurements/2026-10-27-kick-cold-predictions.json) precedes eight different original programs at callbacks8/17/33/127/255/513/1536/3072. Their [prospective comparison](measurements/2026-10-27-kick-cold-holdout.json) passes **8/8**, including frame0, frame1, cold partial callbacks and retriggers. Worst fresh whole-output relative RMS error is **0.007909%**; worst fresh attack/body/decay window is **0.010496%**. All original per-channel 1% gates and fixed32/32 crops remain unchanged. These waveform errors are not perceived-similarity percentages.

The original strict capture checker still rejects the frame0 readback by default. The corrected campaign explicitly selects the measured kick-only control hypothesis: a KickButton=1 request at frame0 must return0; every other requested/immediate/final value must equal its exact prediction. This changes the predicted original control behaviour, not audio acceptance. The first failed prediction remains above.

An [independent audit](measurements/2026-10-27-kick-cold-audit.json) rechecks original receipts, plans, silent input, auxiliary hashes, original binary files and reference-host identity across all **22 programs**. It recomputes every whole/attack/body/decay stereo score using separate arithmetic. All22 optimized and AddressSanitizer/UndefinedBehaviorSanitizer renders are WAV-byte-identical, including zero dry traces, with empty sanitizer stderr and halt-on-error enabled. Negative checks reject a changed prediction, unexpected frame0 acceptance and unexpected rejection of a later press, including when metadata hashes have been rebound. The unchanged default checker still rejects the original first frame0 contract.

Reproduce using [`rmx_kick_cold.py`](../../tools/rmx_kick_cold.py): `regress --set discovery` and `regress --set first-holdout` take `--session`, `--renderer` and a new `--output`; `predict` takes `--renderer --report`; `capture` takes `--renderer --prediction --session --host --plugin`; `compare` takes `--renderer --prediction --session --output`. Build the native research target before predicting. [`rmx_kick_cold_audit.py`](../../tools/rmx_kick_cold_audit.py) accepts three `--dataset KIND SESSION COMPARISON` groups (`discovery`, `first`, `fresh`), plus `--renderer --sanitized --host --prediction --output`; its sanitized build must have compile_commands.json with the verified sanitizer/float flags. Original captures and compiled binaries remain local ignored artifacts.

This is **neutral factory kick research at stereo48k/120BPM**. The live Engine still uses the previous voicing. Wider kick controls and integration remain to be validated. At this checkpoint snare, clap and hi-hat are still unmatched; the next section records subsequent snare progress. Drum work has priority over the remaining Scene FX.

## Snare: first model and fresh validation

The independent [snare model](experiments/SnareResearch.cpp) passes [6/6 discovery programs](measurements/2026-10-27-snare-first-prototype-48k.json). After [freezing that candidate](measurements/2026-10-27-snare-first-predictions.json), eight new original trigger programs at callbacks8/19/35/125/257/515/1537/3073 also [pass8/8](measurements/2026-10-27-snare-first-holdout.json). Worst fresh whole-output relative RMS error is **0.003568%**, and worst fresh attack/body/decay window is **0.003588%**. Every channel/window retains the same1% limit, fixed32/32 timing, and no fitted gain or alignment.

The [numeric observations](measurements/2026-10-27-snare-numeric-observation.json) identify a tone/noise synthesis hypothesis, rather than a stored sample. Two triangles start at phase0.25, with neutral bases168.2Hz and253Hz. A fourth-power pitch envelope briefly raises both frequencies. Absolute-value octave components mix with the triangles, and a shaped amplitude drives a moving bandpass. Seeded XOR/add noise passes through first-order low/high-pass stages and a second-order low-pass, then a shaped noise envelope. The mixed signal is clipped before controller/output gain. The same measured16-sample envelopes,32-sample controller/FIFO and global startup fade provide timing. Static filter coefficients are measured numeric calibration for the explicitly neutral48k model; broader control/rate settings are not implemented by those fixed coefficients.

Runtime observation replaces the static tone decay0.15 with **0.1875 seconds** at factory settings; pitch/noise decays remain approximately0.035/0.49 seconds. A local read-only debugger records64 consecutive subblocks at five stages. The [independent audit](measurements/2026-10-27-snare-first-audit.json) verifies that the debugger render's audio, plan, states, parameter log and inventory are byte-identical to the normal reference. All three envelope trajectories replay64/64 exactly. Both oscillator phase trajectories replay64/64 using the observed pitch envelope; that is a component check, separate from the complete autonomous waveform validation. Raw local instruction listings, original buffers/audio/binaries stay ignored.

The audit independently recomputes every whole/attack/body/decay score in all14 programs, verifies original/candidate provenance, and requires all14 optimized and ASan/UBSan renders to be WAV-byte-identical with zero dry traces and empty sanitizer stderr. Sanitizers run with halt-on-error enabled and their compile flags are recorded. The native synthesis uses no original audio or original DSP calls.

Build `rmx_snare_research_probe`. [`rmx_snare.py`](../../tools/rmx_snare.py) takes the existing discovery `--session --renderer --output`. [`rmx_snare_validate.py`](../../tools/rmx_snare_validate.py) provides the same `predict`, `capture` and `compare` sequence as the first kick campaign, always with new destinations. [`rmx_snare_audit.py`](../../tools/rmx_snare_audit.py) takes `--dataset discovery SESSION COMPARISON` and `--dataset fresh SESSION COMPARISON`, the candidate/sanitized/host/prediction/output paths, and `--debugger --trace --observer` for the retained local read-only observation. The numeric file observer is [`rmx_drum_observe.py`](../../tools/rmx_drum_observe.py).

Current scope is **two independently validated neutral research models: kick22 programs and snare14**. Clap and hi-hat remain unmatched. Neither model is in the live Engine yet. Wider knob laws, alternate decay/envelope profiles, rolls, overlapping instruments, other sample rates and device-level integration remain required. Snare frame0 rejection has not been independently tested; its fresh set starts at frame1 or later.
