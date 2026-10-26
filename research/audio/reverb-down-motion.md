# Reverb Down control motion

27 October 2026. Original RMX-1000 Plug-in 2.2.0, factory Default, Down, stereo 48 kHz, 120 BPM. This investigation extends the [static control model](measurements/2026-10-27-reverb-down-control-interaction-model.json); it does not establish complete Reverb or hardware equivalence.

## Result and scope

The [current stateful research candidate](measurements/2026-10-27-reverb-down-motion-slew-prototype-48k.json) passes 42 of 69 complete renders. These comprise 24 static baselines, two initially disabled impulse cases, eight discovery cutoff-motion cases and eight fresh cutoff-motion cases. The other 27 button, Main, Sub1 and combined-motion cases fail. Production DSP is unchanged.

All 16 cases with only Sub2 moving pass separate whole/wet/post-input-tail screens and whole/wet windows around every event. Eight are prospective captures made after saving the [frozen prediction](measurements/2026-10-27-reverb-down-cutoff-motion-predictions.json). They use new stereo noise/chirp and impulse signals, new Main/Sub1 combinations, control endpoints and knees, rapid reversals while a change is still underway, input gaps, long tails and host blocks of 32/128/256 frames. Main/Sub1 stay fixed and the effect starts enabled in this scoped subset.

The fresh worst whole/wet error is about 0.112%; worst post-input-tail error is 0.00384%. The worst wet event window is **0.9928%**, close to the unchanged 1% limit. That narrow margin warrants further coverage; it is not a claim of numerical identity. The waveform screen never fits gain or wet alignment. Candidate-predicted dry subtraction on both sides is diagnostic and does not independently validate a wet stem.

## Measurements and hypotheses

The [original-versus-original characterization](measurements/2026-10-27-reverb-down-motion-characterization.json) covers the first 61 recordings. Turning the button off during a silent input gap preserves the checked existing tail exactly. Continuous-input differences identify button/input changes on the next 32-frame boundary, followed by the shortest wet delay. Knob effects first appear in raw output at that boundary, one internal block earlier relative to the separately measured 32-frame bypass delay. All six original block repeats are bit-identical.

Cutoff motion exposes a control slew that static recordings could not identify. Sub2 moves **one raw integer step toward its target per 32 samples**. For the first four steps from zero, cutoff stays fixed while compensation rises: original wet/baseline ratios independently recover raw values 1, 2, 3 and 4 on successive blocks. The cutoff law then follows the frozen static map. Target reversals use the current value rather than restarting from the previous target.

The candidate implements the two timing paths causally: fixed input filters and the button input gate feed a 32-frame audio buffer; knobs act on buffered audio. A variable output low-pass retains transposed direct-form-II state, with Sub2 compensation after the filter. Abrupt cutoff updates fail; one-step slew passes. Direct-form-I also passes the four discovery steps but has larger residuals. A direct-form-II realization fails three of those four; these alternatives informed discovery and are not extra acceptance fixtures. Passing does not uniquely identify the original filter implementation.

Main/Sub1 send gain, feedback placement, geometry changes, inactive Main state, button startup and gain fades remain hypotheses. The current renderer also slews Main/Sub1, but their failed comparisons explicitly prevent treating that behavior as identified. Initially disabled continuous-input originals delay first wet output much longer than the shortest static comb delay; the successful spaced impulses do not resolve that startup behavior.

The [first prototype](measurements/2026-10-27-reverb-down-motion-first-prototype-48k.json) passes 26/61. Its source is preserved at `89c5c42`. The current candidate gains eight discovery passes with no previous pass lost, and passes all eight fresh cutoff cases. Both reports retain the failed cases.

## Verification

The [audit](measurements/2026-10-27-reverb-down-motion-audit.json) verifies all 69 exact source/control/event/block/duration recipes, capture hashes, auxiliary state/log hashes, every immediate parameter readback and final control readback. Readbacks are compared at the float32 precision passed to the original plug-in; JSON decimal roundoff is not interpreted as a control change.

A full candidate bypass render is bit-identical to input delayed by 32 frames. Delays of 0, 31 and 33 fail that check. Four independent initially-off original/candidate prefixes are both bit-identical to input at the predeclared 32-frame offset. This justifies the candidate offset without searching wet audio. Seven provenance guards reject modified Main, Sub1, Sub2, event time, host block, tail length and source samples.

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
