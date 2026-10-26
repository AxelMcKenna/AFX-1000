# Reverb Down control motion

27 October 2026. Original RMX-1000 Plug-in 2.2.0, factory Default, Down, stereo 48 kHz, 120 BPM. This investigation extends the [static control model](measurements/2026-10-27-reverb-down-control-interaction-model.json); it does not establish complete Reverb or hardware equivalence.

## Result and scope

The [current stateful research candidate](measurements/2026-10-27-reverb-down-activation-validation-48k.json) passes **98 of 113** complete renders. Passing cases comprise 30 static baselines, 16 cutoff-motion cases, 14 Sub1-motion cases, 26 activation/button-motion cases and 12 isolated gate transitions. Three gate transitions intentionally predict silent wet output. Thirteen Main/combined cases and two immediate-input initialization cases fail. Production DSP is unchanged.

All 16 cases with only Sub2 moving pass separate whole/wet/post-input-tail screens and whole/wet windows around every event. Eight are prospective captures made after saving the [frozen prediction](measurements/2026-10-27-reverb-down-cutoff-motion-predictions.json). They use new stereo noise/chirp and impulse signals, new Main/Sub1 combinations, control endpoints and knees, rapid reversals while a change is still underway, input gaps, long tails and host blocks of 32/128/256 frames. Main/Sub1 stay fixed and the effect starts enabled in this scoped subset.

The earlier fresh cutoff checkpoint's worst wet event window remains **0.9928%**, close to the unchanged 1% limit. The Sub1 checkpoint's fresh worst wet/tail/event-window errors were **0.1939%/0.1365%/0.0989%**; correcting fixed-filter state placement lowers the current 14-case Sub1 regression's worst wet error to **0.0641%**. Eight fresh activation recordings made after freezing the final source/model/renderer pass with worst wet/tail/event-window/startup-window errors of about **0.0041%/0.0039%/0.0044%/0.0043%**. These are scoped software results, not numerical identity or full-device 99% equivalence. The waveform screen never fits gain or wet alignment. Candidate-predicted dry subtraction on both sides is diagnostic and does not independently validate a wet stem.

## Measurements and hypotheses

The [original-versus-original characterization](measurements/2026-10-27-reverb-down-motion-characterization.json) covers the first 61 recordings. Turning the button off during a silent input gap preserves the checked existing tail exactly. Continuous-input differences identify button/input changes on the next 32-frame boundary, followed by the shortest wet delay. Knob effects first appear in raw output at that boundary, one internal block earlier relative to the separately measured 32-frame bypass delay. All six original block repeats are bit-identical.

Cutoff motion exposes a control slew that static recordings could not identify. Sub2 moves **one raw integer step toward its target per 32 samples**. For the first four steps from zero, cutoff stays fixed while compensation rises: original wet/baseline ratios independently recover raw values 1, 2, 3 and 4 on successive blocks. The cutoff law then follows the frozen static map. Target reversals use the current value rather than restarting from the previous target.

The candidate implements the two timing paths causally: fixed input filters and the button input gate feed a 32-frame audio buffer; knobs act on buffered audio. A variable output low-pass retains transposed direct-form-II state, with Sub2 compensation after the filter. Abrupt cutoff updates fail; one-step slew passes. Direct-form-I also passes the four discovery steps but has larger residuals. A direct-form-II realization fails three of those four; these alternatives informed discovery and are not extra acceptance fixtures. Passing does not uniquely identify the original filter implementation.

Main geometry changes, inactive Main state and immediate-input initialization remain unfinished. Sub1 and delayed-input button activation now use the separately verified clocks and fades described below. Their passing scopes do not establish the remaining Main/combined behavior or global startup processing.

The [first prototype](measurements/2026-10-27-reverb-down-motion-first-prototype-48k.json) passes 26/61. Its source is preserved at `89c5c42`. The cutoff checkpoint gained eight discovery passes and passed eight fresh cutoff cases. The staged Sub1 candidate gains another six earlier passes and eight fresh passes, losing no previous pass. Historical reports retain the failed cases.

## Verification

The [current audit](measurements/2026-10-27-reverb-down-activation-audit.json) verifies all 113 exact source/control/event/block/duration recipes, capture hashes, auxiliary state/log hashes, every immediate parameter readback and final control readback. It binds the final activation session to its pre-capture frozen prediction file. The earlier [77-case audit](measurements/2026-10-27-reverb-down-sub1-motion-audit.json) and [69-case audit](measurements/2026-10-27-reverb-down-motion-audit.json) remain preserved. Readbacks are compared at the float32 precision passed to the original plug-in; JSON decimal roundoff is not interpreted as a control change.

A full candidate bypass render is bit-identical to input delayed by 32 frames. Delays of 0, 31 and 33 fail that check. Fourteen initially-off original/candidate prefixes are both bit-identical to input at the predeclared 32-frame offset. This confirms the calibrated offset on those prefixes without searching wet audio; it does not validate immediate-input cold initialization. Seven provenance guards reject modified Main, Sub1, Sub2, event time, host block, tail length and source samples.

Warnings-enabled compilation and two AddressSanitizer/UndefinedBehaviorSanitizer renders pass; both audio and dry traces match optimized builds byte for byte. The linked WAV library was not rebuilt with sanitizers. Tools run in a clean locked uv environment with NumPy and no SciPy.

## Reproduction

Large original recordings and binaries stay under ignored `build/artifacts/research/`. Numeric records bind their hashes. Use the separately acquired original plug-in and reviewed bypass calibration; a project plug-in is not a substitute reference.

Build the standalone candidate:

```sh
clang++ -std=c++20 -O2 -Wall -Wextra -Wpedantic -I include \
  research/audio/experiments/reverb_down_motion_probe.cpp \
  build/uv-migration/librmx_core.a \
  -o build/artifacts/research/reverb-down-motion-probe
```

`uv run --locked python -m tools.rmx_reverb_motion --help` lists capture, recipe verification, original characterization, prospective prediction and comparison commands. Capture the `button`, `steps`, `ramps` and `blocks` stages first. Each destination must be new. `analyze` takes all four sessions and the reviewed calibration.

Before acquiring `cutoff-holdout`, save a new prediction with `predict-cutoff --model MODEL --calibration CALIBRATION --renderer RENDERER --report NEW_JSON`. Its source, recipes, sample hashes, renderer and static model must remain unchanged during capture. Pass this file using `capture --stage cutoff-holdout --prediction NEW_JSON`, along with host, original plug-in, session and calibration paths.

Use `compare --model MODEL --calibration CALIBRATION --renderer RENDERER --quantum 32 --candidate-latency 32 --gate inlet --cutoff-position post --gain-position read --session STAGE DIRECTORY --output NEW_DIRECTORY`, repeating `--session` as needed. A nonzero exit on the complete motion matrix is expected while failures remain. `--case` selects exact diagnostic recipe names, not a replacement for reporting the complete matrix.

`uv run --locked python -m tools.rmx_reverb_motion_audit --help` lists the final audit inputs. Supply all five sessions, the discovery and fresh comparison JSONs, frozen prediction/model/calibration, optimized and sanitizer binaries and a new output directory. Full production integration still requires correct remaining state behavior, fresh broad dynamic validation, fractional controls and production resource/callback checks. Up, other profiles/rates/tempos, overload, listening and hardware remain outside this result.

## Slow state transitions

A further [45 verified original captures](measurements/2026-10-27-reverb-down-state-horizon-characterization.json) separate host-control readback, dry gain, wet-state settling and startup. Twenty-seven short probes include a pre-wet noise burst, early activation impulses and isolated impulses one second after Main/Sub1 changes. Eighteen longer probes place impulses 0.25, 2 or 8 seconds after a change. Every initial/event/final control readback matches its requested float32 value; changed wet timing therefore cannot be explained by a rejected host parameter.

For Main128→192 the first wet delay is 1,085 frames at 0.25 seconds, 1,318 at one second and the static target of 1,536 at two/eight seconds. Main0→128 gives 407, 523 and then the target 1,033 frames at the same horizons. These are observed impulse onsets after subtracting the fixed bypass delay, not fitted waveform alignments. During the transition, cross-channel arrivals need not equal sums of fixed tap lengths; treating the intermediate response as an LTI network is unjustified. Sub1 impulse amplitudes also continue changing beyond a second. The current renderer's one-raw-step-per-32-samples Main/Sub1 update is consequently insufficient even though that rule works for Sub2.

Early button-on pulses at 64 or 4,096 samples produce no meaningful wet response in these fixtures (maximum residual at most about 1.4e-24 after removing the direct impulse). Pulses at 12,000 samples and later enter the expected static delays. This supports investigating a startup inhibit/reset interval; it does not yet identify its exact timing or state action.

The [gain-placement experiment](measurements/2026-10-27-reverb-down-gain-placement-rejections.json) tests global send gain, global return gain and two Main/Sub1 splits. Each passes the selected static baseline and fails all seven selected moving-control fixtures. Moving gain alone is not an accepted fix. The default send path remains byte-identical to the earlier candidate on all eight selected cases. These exploratory failures supplement, rather than replace, the full 42/69 report.

Use `capture --stage state-probes` in the motion tool for the first 27 recordings. `uv run --locked python -m tools.rmx_reverb_state capture-wait --help` describes the 18 horizon captures; its `analyze` command accepts both sessions and the reviewed calibration. Analysis verifies receipt/state/log hashes, exact recipes and immediate/final readbacks before recording onsets and baseline differences. No production DSP or acceptance threshold changes accompany this evidence.

Forty-eight additional isolated-pulse captures resolve the transition more closely. The [93-case state record](measurements/2026-10-27-reverb-down-state-density-characterization.json) includes the earlier 45 cases and these new recordings, with all recipes, hashes and readbacks verified again. Selected Main onsets are:

| Time from control event to input pulse | Main0→128 | Main128→192 | Main192→128 |
| --- | ---: | ---: | ---: |
| 0.125 s | 396 | 1,060 | 1,500 |
| 0.25 s | 407 | 1,085 | — |
| 0.5 s | 435 | 1,142 | 1,405 |
| 0.75 s | 470 | 1,213 | 1,327 |
| 1 s | 523 | 1,318 | 1,223 |
| 1.25 s | 665 | 1,536 | 1,033 |
| 1.5 s | 884 | 1,536 | 1,033 |
| 1.75 s | 1,033 | 1,536 | 1,033 |
| 2 s | 1,033 | 1,536 | — |

Values are first wet output frames minus the exact input-pulse frame and fixed 32-frame bypass delay. A dash means that specific combination was not captured. Main143→144 reaches its target first delay of 1,148 frames by the 0.125-second probe. These observations constrain a future state model; interpolating this sparse table would not establish sample-accurate moving-delay behavior.

Four [linear coefficient hypotheses](measurements/2026-10-27-reverb-down-linear-coefficient-rejections.json) ramp feedback and level coefficients for one or two seconds, using either send or return gain. All 16 checked Sub1 comparisons fail. The best individual reduction still leaves about 6.4% wet RMS error and does not justify selecting a replacement model. A [selected regression/sanitizer check](measurements/2026-10-27-reverb-down-state-experiment-verification.json) confirms that the default zero-ramp path preserves four earlier output/dry traces byte for byte, including the near-limit cutoff holdout, and two experimental sanitizer renders match optimized outputs. The linked WAV library was not rebuilt with sanitizers.

Capture the density stage with `tools.rmx_reverb_state capture-wait --stage density`; add `--density SESSION` to `analyze`. The original accepted cutoff checkpoint, frozen prediction and full 42/69 comparison belong to source commit `b3ca6ff`; use that source version to reproduce its exact source-hash bindings. Later experiments add rejected state hypotheses without expanding the accepted sound-matching scope.

The current CLI defaults to the measured 32-frame control quantum. New predictions explicitly record default send placement and zero coefficient ramp, matching comparison metadata. State analysis rejects sessions bound to another reviewed calibration. [Compatibility checks](measurements/2026-10-27-reverb-down-state-tool-compatibility.json) preserve all 93 findings, reproduce two earlier cutoff output/dry traces byte for byte and reject mismatched calibration, incorrect prediction kind and four invalid renderer options. These two cutoff cases are regressions, not additional prospective captures.

## Sub1 control clock

Separating feedback from level exposes the missing clock. Inspection of the locally installed original binary's DSP symbols and parameter-update path informed this hypothesis; this step is not exclusively black-box identification. Original executables, disassembly and instruction listings remain outside the repository. The experimental implementation uses independently written state machines and the previously measured static coefficient maps.

Sub1 moves one raw step over **five 32-frame blocks**. Its feedback coefficients interpolate during those 160 samples. The return-level target is retargeted at each raw step with a separate linear ramp: **2,600 blocks when increasing Sub1, 2,000 when decreasing**. Retargeting restarts that level ramp from its current value. Main uses a separate adaptive clock and can defer Sub1 work; that interaction is not implemented in this checkpoint.

The [first staged-clock research renderer](measurements/2026-10-27-reverb-down-sub1-clock-prototype-48k.json) passes **48/69**, gaining all four Sub1 steps and both Sub1 ramps without losing a previous pass. Worst wet error among the four steps is about 0.0646%; the fixed whole/wet/tail/event-window gates, gain and bypass-only alignment are unchanged. Main, activation and combined-motion failures remain. This initial report is discovery/regression evidence.

The [gain-trajectory diagnostic](measurements/2026-10-27-reverb-down-gain-trajectory-diagnostic.json) fits a stereo return gain every 32 frames to separate state errors from level errors. Those fitted curves are diagnostic and are explicitly ineligible for waveform acceptance. The [nominal-decay slew trials](measurements/2026-10-27-reverb-down-decay-slew-investigation.json) retain rejected alternatives; one trial passes a single case, but no common decay-slew profile resolves the four steps. The staged renderer uses the identified clock instead of those fitted gains or a selected per-case slew.

Select this candidate using `--level-position output --ramp-components staged` with a newly compiled renderer. Production DSP remains unchanged.

Eight new recordings were then acquired after freezing the [Sub1 prediction](measurements/2026-10-27-reverb-down-sub1-motion-predictions.json). New signals, Main/Sub2 values, raw endpoints/knees, rapid reversals, repeated ramp updates, input gaps and long tails all pass. Host blocks vary between 32, 128 and 256. Only Sub1 moves and the effect starts enabled. The [combined result](measurements/2026-10-27-reverb-down-sub1-motion-validation-48k.json) is 56/77, including all 14 Sub1 cases and all 16 earlier cutoff cases. The earlier cutoff holdouts are regressions for this new candidate, rather than fresh prospective evidence for it.

The [77-capture audit](measurements/2026-10-27-reverb-down-sub1-motion-audit.json) repeats exact bypass checks and seven changed-recipe guards, and verifies two sanitizer renders including a new rapid-reversal Sub1 case. Audio and dry traces are byte-identical between optimized and sanitized builds; the linked WAV library was not rebuilt with sanitizers. Eleven additional [guards](measurements/2026-10-27-reverb-down-sub1-motion-guards.json) reject changed prediction kind, recipe, sources, model, renderer, configuration and five incompatible native modes. All 69 earlier outputs/dry traces are byte-identical between the pre-holdout and frozen guarded binaries. The tooling still uses the locked NumPy-only uv environment.

For prospective replication use `predict-motion --stage sub1-holdout` with model/calibration/renderer/report paths, then `capture --stage sub1-holdout --prediction FROZEN_JSON`. Capture copies the frozen file into the new session. Compare with `--level-position output --ramp-components staged`; this controller requires quantum 32 and a zero generic coefficient-ramp argument. The audit accepts this prediction stage and exercises the same renderer configuration for its bypass and sanitizer checks.

## Remaining state rules to implement

Control-path inspection also identifies a proposed Main clock consistent with the measured horizons. It begins with a period of 60 blocks. Before each adjacent raw step, the desired period is `15 - min(5, abs(target-current))`; the current period moves one block toward that value. Delay and feedback targets interpolate over the chosen period, then the raw step commits. The period persists across subsequent changes, and Main work can defer Sub1 updates. Starting from period 60 predicts 60,000 samples for Main128→192 and 80,480 for Main0→128. This rule is not yet implemented or accepted as a Main waveform match; fractional delay state, hidden inactive geometry and input/output gain placement still need verification.

The initial activation path fills comb history while suppressing wet feedback/output for 388 blocks (12,416 samples). Early impulses are overwritten while later input is already available when normal processing begins. The activation work below implements this rule, input/dry fades and an extra preparation block for an initially active effect. Immediate-input global initialization still fails, and Up, other profiles/rates/tempos, overload, listening and hardware remain unproven.

## Activation discovery checkpoint

Eighteen new original impulse probes distinguish six always-on baselines, six off transitions and six on transitions. Their [fixed-gate prediction](measurements/2026-10-27-reverb-down-button-gate-prediction.json) verifies a float32 step of 1/160 per input sample in both directions, beginning at the next 32-frame boundary. Twelve complete wet impulse responses agree with their baselines scaled by the predicted gate value; no gain is fitted. Three transition fixtures intentionally predict silent wet output and are identified separately. This is component evidence, separate from autonomous rendering.

The startup candidate fills comb history without feedback or wet output for 388 blocks. One right-channel comb history stays empty during this interval. A candidate that filled that history produced the observed immediate right-channel error and a left-channel error exactly one paired left delay later; leaving it empty resolves both. The 54 Hz fixed high-pass operates after the diffusers in this candidate, and dry gain uses a separate 160-sample ramp with an initial one-block restart. Control-path inspection informed these hypotheses; original recordings verify their resulting behavior.

The [activation research prototype](measurements/2026-10-27-reverb-down-activation-prototype-48k.json), selected with `--gate faded --level-position output --ramp-components staged`, passes **82/95**. On the earlier 77 cases it gains all eight remaining activation/button-block passes, with no previous pass lost. All 18 new gate probes also pass; their six static baselines and expected-silence transitions are not presented as independent active-program validation. All 12 button-stage cases pass, with active transition wet errors below 0.0005%. Thirteen Main/combined failures remain. Fresh prospective activation validation is still required; production is unchanged.

Use `capture --stage button-probes` for the 18 recordings and `uv run --locked python -m tools.rmx_reverb_activation --help` for the component prediction check. Original binaries and disassembly remain untracked build artifacts; no original instruction listing is distributed with this implementation.

The [first frozen activation prediction](measurements/2026-10-27-reverb-down-activation-first-predictions.json) was checked on eight new captures with changed signals/settings, initial states, rapid toggles and a long off interval. [Seven pass and one fails](measurements/2026-10-27-reverb-down-activation-first-holdout-48k.json). The failing rapid cold-toggle fixture exposes four dry-fade endpoint samples: the candidate snaps to its target before emitting the last sample, while the original emits the accumulated float32 value and snaps afterward. The largest pre-wet output discrepancy is about 3.17e-8. The candidate-predicted dry subtraction exposes this in the strict wet event window, even though whole wet RMS error is below 0.002%. The gate is unchanged and the failure remains recorded; correcting the update order requires another prospective set.

## Activation prospective validation

The revised candidate emits the accumulated float32 dry-fade endpoint before snapping state. Boundary-aligned parameter events enter the following 32-frame control block, and initially active preparation takes an extra block. These changes resolve the first failed holdout and reduce the other timing residuals. The [original failed report](measurements/2026-10-27-reverb-down-activation-first-holdout-48k.json) and source checkpoint `181a473` remain preserved.

After freezing a [second prediction](measurements/2026-10-27-reverb-down-activation-predictions-v2.json), all eight new activation captures pass the strengthened whole/wet/tail/event and activation-start windows. Signals, Main/Sub1/Sub2 values, pulse times, host blocks and toggle schedules differ from the first set. Coverage includes rapid cold toggles, exact 32-frame boundaries, short on/off gaps and a long off interval. The first set is now regression evidence; only this second set is prospective validation for the final candidate.

The [complete 113-case report](measurements/2026-10-27-reverb-down-activation-validation-48k.json) preserves all earlier passes and gains eight earlier button/activation passes. Both eight-case activation sets pass, alongside all 16 cutoff and 14 Sub1 cases. It retains 13 Main/combined failures and two source-from-frame-zero initialization failures. Activation-start windows additionally check the delayed wet onset; their anchors come from the fixed control clock and startup count, without fitting alignment.

The fresh activation programs begin with 0.25 seconds of input silence. Two additional recordings begin with non-silent input at frame zero and fail: Main128 has roughly 2.9–3.2% whole and 4.8–5.3% wet error; Main255 has roughly 3.6–3.7% whole/wet error. They expose global input-source startup and initial dry-path preparation beyond the validated delayed-input scope. These failures stay in the full matrix and remain part of the sound-matching goal.

The [113-capture audit](measurements/2026-10-27-reverb-down-activation-audit.json) verifies frozen predictions, provenance, all readbacks, 14 bypass prefixes, seven changed-recipe guards and two sanitizer renders. Optimized/sanitized output and dry traces are byte-identical; the linked WAV library was not rebuilt with sanitizers. Eleven additional [prediction/native-mode guards](measurements/2026-10-27-reverb-down-activation-guards.json) pass in the clean locked NumPy-only uv environment.

To reproduce, freeze `predict-motion --stage activation-v2-holdout`, capture that stage with `--prediction`, then compare using `--gate faded --level-position output --ramp-components staged`. Include `button-probes`, `initialization-probes` and the earlier sessions for the complete matrix. The auditor selects the same renderer configuration for bypass and sanitizer checks. Production integration and full sound equivalence remain unfinished.
