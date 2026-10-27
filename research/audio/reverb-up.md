# Reverb Up network identification

27 October 2026. Original RMX-1000 Plug-in 2.2.0, factory Default Up, stereo 48 kHz, 120 BPM. This record covers static integer Main/Sub1 controls and the measured Sub2 filter. The later [motion/startup investigation](reverb-up-motion.md) passes 101 motion cases and reruns all 1,204 static cases through a stateful research processor. The subsequent [live Engine checkpoint](reverb-up-motion.md#live-engine-integration-27-october-2026) passes 1,321 scoped cases. Hardware equivalence remains unfinished. The [reference-method guide](reference-method.md) explains the experiment's general rules.

## Current static-control result

The [static control model](measurements/2026-10-27-reverb-up-static-control-model.json) passes [1,204 complete waveform cases](measurements/2026-10-27-reverb-up-static-control-validation-48k.json): **1,024 coefficient-calibration captures, 52 earlier fixtures, 64 regressions from the first mixed set, and 64 new prediction-bound mixed captures**. It independently generates the wet signal from source audio and declared controls. Fresh worst whole/wet/tail errors are about **0.000724%/0.000800%/0.00164%**; overall worst wet/tail errors are about **0.00147%/0.00264%**. The unchanged limit is 1% per channel, with fixed reference/candidate crops32/0 and no comparison gain fitting or wet alignment search.

This is a scoped static research result, not 1,204 blind tests, an exhaustive 65,536-pair waveform sweep, a perceptual score or full-device 99% equivalence. The live Engine's Up path remains approximate. The sections below preserve how the model developed, including the failed first coefficient and mixed-control predictions.

## Neutral-setting checkpoint

The [autonomous static candidate](measurements/2026-10-27-reverb-up-neutral-validation-48k.json) passes **28/28** complete whole/wet/post-input-tail comparisons. Twenty are existing identification/development/component recordings; eight were newly captured after [freezing the candidate](measurements/2026-10-27-reverb-up-neutral-predictions.json). The new set uses two new stereo programs, each at four previously untested cutoff positions: 19, 111, 203 and 247. Audio starts after a one-second silent pre-roll. Duplicated calibration baselines and silence are included in the count and annotated by role.

Fresh worst whole/wet/tail per-channel relative RMS errors are about **0.0013%/0.0026%/0.0039%**. Across all 28 cases, worst wet/tail errors are about **0.0033%/0.0047%**. Every screen retains the 1% limit, reference-channel summed-energy floor `1e-20`, silent-channel absolute RMS limit `1e-8`, reference crop32 and candidate crop0. No comparison gain or wet alignment is fitted. The static dry trace is input at unity; the candidate independently generates the complete reverberation, without a reference wet stem or original reverb output as its input.

The [research C++ renderer](experiments/reverb_up_neutral_probe.cpp) is separate from the live Engine. The Engine's Reverb Up remains the earlier approximation. At this neutral checkpoint, Main/Sub1 maps had not been established; the later static-control work below supplies that separate evidence. Moving controls, cold input, activation, other profiles/rates/tempos, overload, listening and physical hardware remain unfinished.

## What changed from Down

A straightforward reuse of Down's network misses Up's frequency-dependent feedback. The [identification record](measurements/2026-10-27-reverb-up-neutral-model.json) supports five paired cross-coupled combs, followed by the same two all-pass stages per channel, with these neutral-setting delays:

| Pair | Left frames | Right frames |
| --- | ---: | ---: |
| 1 | 509 | 565 |
| 2 | 523 | 915 |
| 3 | 565 | 967 |
| 4 | 945 | 550 |
| 5 | 983 | 587 |

Up adds a **25 Hz first-order high-pass in each comb's feedback path**. The return sums taps before that filter. Input instead passes through a second-order band-pass with fitted poles, rather than Down's fixed 80 Hz high-pass/10 kHz low-pass pair. At this control point, its equivalent center/Q are approximately 437 Hz/0.607. Its numerator is proportional to `1-z^-2`; gain is separately identified. Output retains the measured variable 54..6310 Hz high-pass, fixed 17,330 Hz low-pass, and `1 + 0.5*Sub2Raw/255` level compensation. All-pass delays are left335/1091 and right395/1031, with gain0.7.

This structure was not inferred exclusively from black-box recordings. Inspection of the locally installed original's control/DSP path suggested an Up-only input biquad and feedback high-pass. No original executable, disassembly or instruction listing is distributed. Independent I/O measurements determine the committed numeric calibration and test the resulting model; topology remains an empirical candidate rather than manufacturer attribution. The [manufacturer documentation index](https://www.pioneerdj.com/en/support/documents/rmx-1000/?all=0) is an external entry point for user manuals, not evidence for these hidden coefficients.

## How it was identified

The [tool](../../tools/rmx_reverb_up.py) first verifies the original left/right impulse recordings against exact samples, settings, extent and receipt hashes. A regularized inverse using the earlier Down transfer locates candidate arrival times only; it is deliberately not accepted as Up's input-filter model. A unique pairing of left/right delays must reproduce the cross-channel arrival sums. Removing the diffuser phase makes the two cross-channel transfers agree to about 5.3e-7 relative error, supporting the shared diffuser/symmetric-network hypothesis.

For one pair, write `L=gL*z^-dL`, `R=gR*z^-dR`, and `H` for the feedback high-pass. Left-input direct/cross transfers are:

```text
left  = L / (1 - L*R*H^2)
right = L*R*H / (1 - L*R*H^2)
```

Sum those transfers across the five pairs, then apply the shared input filter, output filters and channel diffuser. The stereo transfer ratio cancels the shared input/output filter. This permits fitting scalar feedback gains from the left-input recording before fitting the input band-pass. Right input informs geometry/diffuser symmetry; it does not supply the feedback/input-filter gain fit.

The rejected unfiltered-feedback hypothesis has about **10.39% stereo frequency-ratio residual**. Including the feedback high-pass lowers that component residual below `1e-4`; the complete fitted frequency response has about **0.0024%** relative error. These are identification screens, not substitute waveform acceptance tests. Full time-domain renders and the later fresh recordings provide the separate acceptance evidence.

## Audit and implementation checks

The [28-capture audit](measurements/2026-10-27-reverb-up-neutral-audit.json) verifies all recipes, receipts, state/log/inventory hashes, every immediate/final readback, comparison output hashes, the frozen source/model/renderer/sample binding and the fresh session's copied prediction. Twenty-seven initial direct-only prefixes, 128 samples each, are bit-identical across original, candidate and input; the silent case stays zero. A one-frame candidate shift fails both whole and wet gates.

Five changed-recipe guards, seven changed-prediction guards and nine invalid/existing-output requests are rejected. The shared WAV loader's separate non-finite policy is checked explicitly: NaN input is replaced with zero and renders silence. Numeric control NaNs are rejected. An initial audit test had incorrectly assumed the loader rejected NaNs; the corrected check follows the existing loader contract without changing the candidate or waveform gates.

Two full candidate renders are byte-identical between optimized and AddressSanitizer/UndefinedBehaviorSanitizer builds. Compile recipes and fresh object hashes confirm that the research DSP and shared WAV IO were instrumented. Eight relevant core CTest groups pass. The [verification summary](measurements/2026-10-27-reverb-up-neutral-checks.json) records these checks and their hashes. Whole-file WAV buffers allocate in this offline fixture; this is not an MCU/callback qualification.

## Reproduce

Use the separately acquired original plug-in, compatible Intel reference host, reviewed 48 kHz bypass calibration, and earlier initial/filter sessions. Original binaries and captures stay under ignored `build/artifacts/research/`; committed records retain hashes and numeric findings.

```sh
uv sync --locked
cmake -S . -B build/reverb-up -DCMAKE_BUILD_TYPE=Release \
  -DRMX_BUILD_PLUGINS=OFF -DRMX_BUILD_REFERENCE_HOST=OFF
cmake --build build/reverb-up --target rmx_reverb_up_probe
uv run --locked python -m tools.rmx_reverb_up --help
uv run --locked python -m tools.rmx_reverb_up_audit --help
```

Run `identify --initial INITIAL_SESSION --calibration CALIBRATION --report NEW_MODEL --header NEW_HEADER`. Compare a regenerated header to the [committed calibration](experiments/ReverbUpNeutralCalibration.h) before deliberately replacing/rebuilding it; reports and headers must be new. `predict --model MODEL --calibration CALIBRATION --renderer RENDERER --report NEW_PREDICTION` freezes the candidate before `capture --prediction NEW_PREDICTION`, with the original host/plug-in and new session directory.

Use `compare --model MODEL --calibration CALIBRATION --renderer RENDERER --session initial INITIAL_SESSION --session filters FILTER_SESSION --session holdout HOLDOUT_SESSION --output NEW_DIRECTORY`. The comparator fixes reference/candidate offsets at 32/0. The audit accepts all three sessions, comparison JSONs, frozen prediction/model/calibration, optimized and sanitizer renderers, its sanitizer build directory and a new output directory. Build the complete sanitizer core/fixture with `-fsanitize=address,undefined` compiler/linker flags, `-fno-omit-frame-pointer`, and exported compile commands. Historical frozen hashes require their recorded source version.

The neutral checkpoint led to the Main/Sub1 measurements below. The later [motion/startup checkpoint](reverb-up-motion.md) supplies separate measured evidence. Runtime qualification and live Engine integration remain required; passing a static model does not complete full-device 99% fidelity.

## Dense controls: first identification checkpoint

Two 256-position sweeps now measure Main at Sub1-128 and Sub1 at Main128. All 512 recordings pass their coefficient-structure fitting screen, but the [saved Sub1 forecast](measurements/2026-10-27-reverb-up-control-first-checkpoint.json) fails its unchanged `2e-6` gain-coefficient limit at **155/256 positions**, with worst error about `2.45e-5`. The [first amount report](measurements/2026-10-27-reverb-up-amount-first-identification.json) retains every failed forecast; this is not an accepted full-control waveform model.

The [Main identification](measurements/2026-10-27-reverb-up-main-first-identification.json) supports a fourth-power shrinking-room curve, suggested by eight earlier positions. Its straightforward float32 expression predicts 2,519 of 2,520 active integer taps exactly; Main104's fifth left tap is measured at 1,368 frames rather than the predicted 1,367. The curve assessment is retrospective, since dense capture was already underway. Exact measured delays remain authoritative. Feedback-filter arithmetic/identification precision needs investigation before reusing the neutral gains as a Sub1 scaling anchor. No live Up DSP changes accompany this checkpoint.


## Feedback arithmetic and the first mixed-control failure

The next [development checkpoint](measurements/2026-10-27-reverb-up-static-development-checkpoint.json) retains a correction and a separate failure. It is not a new full-control acceptance claim.

### Why the Sub1 coefficient forecast failed

The nominal 25 Hz feedback high-pass was initially calculated in double precision. Read-only scalar inspection of the installed original found stored coefficients `b0=0.9983664155006409`, `b1=-0.9983664155006409`, `a1=-0.9967328906059265`. These differ from the ideal nominal calculation. The [observation record](measurements/2026-10-27-reverb-up-feedback-arithmetic-observation.json) preserves numeric facts and binary/log/script hashes. The debugger-rendered original audio is byte-identical to the corresponding original capture; the debugger did not modify DSP state. Original instructions and raw debugger artifacts are not distributed.

Refit only the existing Main128/Sub1-128 calibration using these measured feedback coefficients to obtain a [revised reference](measurements/2026-10-27-reverb-up-control-reference.json). Apply `g(Main,Sub1) = g(Main,128) ** (T128/TSub1)`, with `T(raw)=1+49*(max(0,raw-3)/252)^3`. Refitting the old Sub1 sweep now gives a worst coefficient discrepancy of about `7.47e-7`; that is retrospective evidence. The [revised report](measurements/2026-10-27-reverb-up-amount-corrected-identification.json) still explicitly records the original failed forecasts.

Then [freeze eight new forecasts](measurements/2026-10-27-reverb-up-feedback-corrected-predictions.json), change the input impulse from +0.02 at frame48000 to -0.019 at frame72013, and capture Sub1 positions 0/5/31/83/131/179/227/253. All [eight new coefficient checks pass](measurements/2026-10-27-reverb-up-feedback-corrected-validation.json), worst error about `7.37e-7`, retaining the original `2e-6` limit. This validates the coefficient hypothesis in this scope; it does not replace full waveform checks. Reproduction commands are in [`rmx_reverb_up_feedback.py`](../../tools/rmx_reverb_up_feedback.py): `refine-reference`, `predict`, `capture`, then `validate`.

### Why every integer delay matters

Use the [corrected dense Main measurements](measurements/2026-10-27-reverb-up-main-corrected-identification.json), including Main104's measured 1368-frame fifth left tap. The [negative control](measurements/2026-10-27-reverb-up-one-frame-negative-control.json) deliberately shortens only that tap to the formula's 1367 frames. Wet error jumps to about **47.8%** in each channel and fails the fixed limit. This demonstrates why a visually convincing room-size curve cannot replace exact measured integer geometry. Build `rmx_reverb_up_one_frame_probe` to reproduce the altered candidate; it is excluded from the default build.

### Separate calibration from new combinations

The [first static control candidate](measurements/2026-10-27-reverb-up-static-separable-model.json) uses measured Main rows, the decay exponent above and a separable Main/Sub1 wet gain. Its 564 existing/calibration waveform cases pass all whole/wet/tail screens: 512 dense sweep recordings plus 52 earlier Up fixtures. Worst wet/tail relative RMS errors are about **0.00147%/0.00113%**. All [28 legacy neutral outputs](measurements/2026-10-27-reverb-up-legacy-neutral-parity.json) remain byte-identical through the original four-argument invocation.

Before new recordings, [freeze the model, renderer, source files, source samples and 64 mixed recipes](measurements/2026-10-27-reverb-up-mixed-first-predictions.json). Two new stereo programs exercise 32 control combinations each, including zero/edge positions, Main104, long tails, and four cutoff positions. The [first mixed result](measurements/2026-10-27-reverb-up-mixed-first-validation.json) passes **52/64**, with **12 failures** at long Sub1 settings. Wet/tail errors reach about **3.224%**; several whole-output errors are much smaller because dry audio masks the mismatch. The unchanged 1% wet/tail gates correctly reject the candidate.

The similar error for broad-spectrum and impulse programs suggests a Main/Sub1 level interaction, but that remains a hypothesis until separately measured. Preserve this failed candidate and report before changing it. Next measure Main across its full range at Sub1-255 and Sub1 across its full range at Main255, fit an interaction map only from those calibration sweeps, then freeze a different mixed program set before further original captures. The failed 64 become regressions for a revised candidate, not new validation of that revision.

[`rmx_reverb_up_controls.py`](../../tools/rmx_reverb_up_controls.py) provides `capture`/`identify` for `main`, `amount`, `main-long` and `amount-large`. [`rmx_reverb_up_model.py`](../../tools/rmx_reverb_up_model.py) provides `build`, `predict`, `capture` and `compare`. Use `--help` for exact arguments. Every destination must be new; historical frozen bindings require the recorded source checkpoint. Full control auditing, moving controls, startup, live Engine integration, other rates/profiles/tempos, overload, listening and hardware remain unfinished.


## Measured interaction and a further fresh set

The retrospective [failed-case level diagnostic](measurements/2026-10-27-reverb-up-mixed-first-level-diagnostic.json) nearly removes the residual with one constant scale per case. That supported investigating level, but those fitted scales were never used for waveform acceptance or to calibrate the final interaction map.

Instead, capture two additional dense axes: [Main0..255 at Sub1-255](measurements/2026-10-27-reverb-up-main-long-identification.json), then [Sub1-0..255 at Main255](measurements/2026-10-27-reverb-up-amount-large-identification.json). The 512 recordings use the same +0.02 left impulse and three-second tails as the first axes. They each carry feedback forecasts saved before capture. All coefficient fits and assessable forecasts pass; worst gain errors are about `2.94e-7` and `1.49e-7`, below the unchanged `2e-6` limit. Four zero-wet Main positions do not expose internal geometry/gains and are explicitly unassessable for that forecast.

Let `G(M,A)` be the identified wet gain, `B(M)=G(M,128)`, and `U(A)=G(128,A)/G(128,128)`. Use a separable correction to the initial level map:

```text
C(M) = G(M,255) / (B(M)*U(255)) - 1
D(A) = (G(255,A) / (B(255)*U(A)) - 1) / C(255)
model wet gain(M,A) = B(M)*U(A)*(1 + C(M)*D(A))
```

This is an empirical model, not a manufacturer specification. Zero-wet Main rows use `C=0`; their hidden state remains unqualified for motion. Across the integer map, the correction factor ranges from about **0.96877 to 1.03264**, explaining the earlier roughly 3% failures. The feedback exponent, measured integer delays, input filter and Sub2 output filter retain their separately identified forms. No scale is estimated from the waveform being judged.

The builder requires both interaction reports to match their frozen separable base model, corrected reference and calibration. [Seven invalid provenance/fit inputs](measurements/2026-10-27-reverb-up-static-builder-guards.json) are rejected before writing a model/header. Positive level and stable feedback/input-filter math are checked over all 65,536 integer combinations; these checks are not 65,536 audio comparisons.

All 1,140 existing/calibration cases pass with this revised candidate. Then [freeze a second mixed set](measurements/2026-10-27-reverb-up-mixed-second-predictions.json): change program seed/chirp/tones, impulse times, Main/Sub1 pairs and cutoff positions, retaining the same 1% gates, source-sample hashing, original host and 32/0 offsets. All **64 newly captured cases pass** complete whole/wet/post-input-tail screens, including 18- or 90-second tails. Combined total is **1,204/1,204**. The first candidate's 12 failures and frozen source remain at `a6dff02`; its original coefficient failures remain at `2a827bd`.

### Final audit and implementation checks

The [static-control audit](measurements/2026-10-27-reverb-up-static-control-audit.json) rechecks all 1,204 recipes/receipts/auxiliary hashes, every immediate/final parameter readback, shared original host/bundle identity, and all candidate file hashes. It recomputes every whole/wet/tail screen. The new mixed session must match the current frozen prediction; the prior mixed session retains its earlier frozen candidate and is explicitly a regression. All **1,203 non-silent input prefixes** are bit-identical across original/candidate/input over their first 128 direct-only frames; the silent-input case stays zero.

It also rechecks the debugger/original input, plan, audio, host and bundle hashes plus scalar script/log hashes, and repeats all eight corrected-reference coefficient forecasts. Five changed recipes, nine changed prediction/model bindings and eighteen invalid/existing-output native requests are rejected. The shared WAV loader's NaN-to-zero behavior is separately confirmed. The one-frame Main104 network perturbation still fails at roughly 47.8% wet error.

Two full optimized/sanitized renders are byte-identical, including a fresh stereo program. Compile recipes, object freshness and object/source/calibration hashes verify instrumentation of DSP and shared WAV IO with AddressSanitizer/UndefinedBehaviorSanitizer. All [28 legacy neutral outputs remain byte-identical](measurements/2026-10-27-reverb-up-legacy-neutral-interaction-parity.json). Eight relevant core CTest groups pass; the [check record](measurements/2026-10-27-reverb-up-static-control-checks.json) binds these results. Offline whole-file allocation remains; there is no callback deadline, fresh firmware cross-build or hardware claim.

### Reproduce the interaction model

After retaining the first candidate and failed report, use `capture --stage main-long` and `capture --stage amount-large` with `--neutral CORRECTED_REFERENCE --static-model SEPARABLE_MODEL`, then `identify` for each session with the same inputs. Build the revised model into **new** destinations:

```sh
uv run --locked python -m tools.rmx_reverb_up_model build \
  --main MAIN_REPORT --amount AMOUNT_REPORT --neutral CORRECTED_REFERENCE \
  --calibration CALIBRATION --feedback-validation FRESH_COEFFICIENT_VALIDATION \
  --main-long MAIN_LONG_REPORT --amount-large AMOUNT_LARGE_REPORT \
  --interaction-base SEPARABLE_MODEL --report NEW_MODEL --header NEW_HEADER
```

Review the generated header against `ReverbUpControlCalibration.h`, deliberately install/rebuild it, and compare all prior sessions. Use `predict --recipe mixed-v2`, then `capture --recipe mixed-v2 --prediction NEW_PREDICTION` with original host/plug-in and a new session; `compare --session mixed-v2 NEW_SESSION` renders the independently implemented candidate. Preserve complete original tails rather than using the damped identification response as an acceptance substitute.

Run `uv run --locked python -m tools.rmx_reverb_up_model_audit --help` for the audit arguments. Supply the eleven named sessions, three component comparison reports, current/first mixed predictions, corrected reference/coefficient validation, original read-only observation artifacts, optimized/one-frame/sanitizer renderers and sanitizer build directory. The audit checks the installed original bundle and requires unchanged historical source bindings. Published numeric records omit large captures and raw debugger artifacts; reproducing those checks requires the separately acquired original and locally generated sessions.

Current scope is **static integer controls with settled silent pre-roll, factory Up, stereo 48 kHz/120 BPM**. Moving controls, activation/cold startup, fractional controls, other profiles/rates/tempos, live Engine integration, overload, listening and physical hardware remain required by the full sound-matching goal.

The subsequent [motion/startup investigation](reverb-up-motion.md) passes 101 motion cases, including sixteen fresh recordings after correcting a failed first holdout, and all 1,204 static regressions. Its independent audit, failed forecasts, gain/clock derivation and 40-sample read-window discovery are documented separately. The live Up Engine remains approximate.

The [bounded core class](reverb-up-motion.md#bounded-core-processor-27-october-2026) subsequently preserves all 1,305 research output/dry WAVs byte-for-byte and passes eight further fresh motion/startup programs. Native resource checks measure bounded storage and zero tracked callback allocations. Live Up Engine integration is still pending.

The [live Up Engine](reverb-up-motion.md#live-engine-integration-27-october-2026) now passes 1,321 scoped waveform cases, including eight new prediction-bound programs, with AU/VST3 and preserved Down checks. Earlier statements about an approximate live Up path describe their historical checkpoint. Other profiles/rates, combinations and full-device fidelity remain incomplete.
