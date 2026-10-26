# Spiral core identification, 26 October 2026

The original 2.2.0 plug-in now has reproducible experiments for separating its linked level measurement, clipping, linear filters and internal repeat clock. The [component identification](measurements/2026-10-26-spiral-core-identification.json) records 42 selected reference captures and verification of 94 input/control recipes. These are software observations at Default, Main raw 128, Sub2 zero, 48 kHz and 120 BPM unless explicitly labeled otherwise. No manufacturer implementation or recorded audio is included in the source tree.

The experimental complete model **fails** the [expanded 343-render comparison](measurements/2026-10-26-spiral-envelope-prototype-48k.json): 273 pass and 70 fail. It is a research fixture, separate from the production engine. Its partial successes do not establish full Spiral or device similarity. The [initial ten-render comparison](measurements/2026-10-26-spiral-core-prototype-48k.json) and [208-render clock checkpoint](measurements/2026-10-26-spiral-neutral-clock-prototype-48k.json) remain as historical records.

## What the new experiments establish

The stereo level measurement operates in groups of 32 input frames. A right-channel pulse is compensated so the instantaneous stereo sum reaches the same peak at different positions. Moving that pulse anywhere within the first group leaves the complete left output bit-identical. Positions in later groups move its response accordingly. Host blocks of 32, 128 and 256 produce identical checked recordings, establishing that this grouping belongs to the reference processing rather than the capture host.

Equal and opposite tones produce zero wet output. Changing the right input, including adding positive or negative DC, changes the left wet level substantially. The peak measurement is therefore linked across channels. Quiet differential pulses after a common high-level preconditioning signal leave the unchanged left response bit-identical across same/opposite/asymmetric right pulses. A mono differential pulse creates no right-channel difference. These quiet tests rule out direct linear crossfeed as an explanation of the observed level coupling; they do not establish nonlinear channel independence.

Holding the stereo sum high while sending much smaller left impulses exposes a linear first pass. A tenfold impulse change at two DC levels gives the same normalized response within roughly 0.00003% RMS error. Identification windows end before the next internal repeat: 2,048 frames compared with approximately 2,496 frames for Up and 12,144 for Down. DC is an offline diagnostic fixture, not a proposed hardware stimulus.

The first-pass clipping response is explained by a 12 kHz, Q 0.707 input low-pass followed by clipping. Joint fits of quiet linear and two clipped impulse cases have normalized errors below 0.00003%. A 32-tap output-shaping calibration and three slow real filter poles reproduce those windows. Their placement around a complete nonlinear feedback processor is not established by these fits alone.

Quiet internal repeats identify an additional 12.1 kHz, Q approximately 0.7 low-pass and two high-pass sections. Their small-signal loop gains are approximately 1.5 for Up and 1.2 for Down. First-return component fits have errors below 0.00005%. Fractional repeat positions drift by approximately two parts per million even at the neutral pitch setting. Repeated quiet impulses distinguish that drift from a constant fractional delay. The record retains the measured fractions rather than attributing the drift to an unverified implementation detail.

The measured first-block threshold is about `0.002673797 * peak(abs(L+R))`. Interpreting this as half a smoothed envelope suggests a block smoothing coefficient near 0.005347594. That separation is a model convention; the first-block fit alone identifies their product. The envelope experiments below identify a candidate release law. Its exact arithmetic and remaining feedback interactions are unresolved.

## A deliberately incomplete model

[spiral_neutral_probe.cpp](experiments/spiral_neutral_probe.cpp) combines these components with a candidate peak-hold envelope and feedback arrangement. Its [calibration header](experiments/SpiralNeutralCalibration.h) is generated from the numerical identification. It accepts only Main raw 128, neutral Sub2, 48 kHz and 120 BPM; Sub1 selects the separately validated outer return.

The initial model passed four complete mono/square tone cases and failed six complete sparse-impulse, DC-conditioned and stereo broadband cases. Its largest passing wet error was about 0.017%. Those historical failures remain in the initial report.

The clock and peak-order checkpoint passed 110 of 208 eligible complete renders. The release correction now passes 150 of that same 208, adding 40 passes without losing a previously passing case. All 104 original Down cases pass. The larger 343-case campaign adds 135 envelope fixtures; 273 pass and 70 fail. One added Down DC/query fixture still fails, alongside many Up sparse and channel-transient cases. Largest passing wet-channel error is about 0.695%. The aggregate comparison returns exit code 1. A one-percent waveform RMS screen is not a perceptual similarity percentage, and a pass count is not device accuracy.

The failed cubic-feedback, extra-clipping and filter-state rearrangement experiments remain local diagnostics. The next identification step must explain the remaining Up tails and the added Down failure while preserving the measured input, timing and quiet linear responses. Other Main positions, nonzero pitch, gestures, User settings, overload and hardware require separate validation.

## Clock and peak-order refinement

A fresh 34-second original Down recording keeps the right input at DC 0.2 and injects a single left impulse of amplitude `1e-12`. This is an offline numerical fixture. The small left response remains below clipping through more than 100 internal repeats. The [long-clock record](measurements/2026-10-26-spiral-neutral-clock.json) retains 119 separate repeat fits and 31 complete one-second comparisons of the quiet left channel. The right DC channel is explicitly excluded from this component screen.

The measured fractional delay rises toward one sample around ten seconds, reverses, crosses zero around twenty seconds, and reverses again near thirty seconds. Both an unbounded ramp and a simple sawtooth reset miss this behavior. A fixed empirical model uses the fractional part of a triangular phase:

```text
u = 2.086162567138672e-6 * (32 * floor(frame / 32) - 64)
t = 1 - abs(((u + 1) mod 4) - 2)
delay = integer_delay + t - floor(t)
```

This is an observed model, not a claim about the manufacturer's implementation. The per-repeat component-fit RMS errors stay below 0.0015%; measured fractions differ from this model by less than 0.00027 sample. The complete left-channel comparisons use the fixed renderer, the reviewed bypass offset and the known stimulus amplitude on both sides, with no wet alignment or fitted candidate gain. Worst one-second error through 32 seconds is about 0.31%. The previous unbounded-clock renderer fails the same complete-window check, reaching about 181% error.

Variable-peak white noise also distinguishes smoothing order. Smoothing every 32-frame peak first, then taking a held maximum, reproduces these cases much better than updating the envelope only when the raw peak exceeds the held envelope. Constant-peak random binary input provides a control. The candidate now uses `smoothed += alpha * (peak - smoothed); held = max(held, smoothed)`. These successes support that ordering in this candidate; they do not resolve release behavior or the nonlinear feedback model.

An isolated right-channel cue can still fail while the simultaneous continuous left tone matches closely. This prevents treating the sparse failures as merely a shared output-gain correction. The candidate remains outside the production DSP.

## Activity and release refinement

[tools.rmx_spiral_envelope](../../tools/rmx_spiral_envelope.py) adds 135 exact input/control recipes. A left preconditioner establishes a held level; a later right impulse measures its clipping threshold before the first right-channel repeat. The right channel is otherwise untouched, except in the stereo-reset stage, where the known linear residue of an earlier unclipped control is subtracted. The [identification record](measurements/2026-10-26-spiral-envelope-identification.json) retains all first-pass fits, capture hashes and a failed prospective hypothesis. Every first-pass fit has relative RMS error below 0.0001%; this is component identification, not complete-effect matching.

Down's sparse threshold falls in discrete one-decibel steps. At delays of 0.25, 0.5, 1 and 2 seconds after the initial pulse, the measured ratios are approximately 0.794328, 0.630957, 0.398107 and 0.158489. The two-second ratio holds across initial pulse amplitudes from 0.0001 to 0.8. Up holds the initial threshold over the checked gaps; both directions hold after a continuous mono tone. Small controls that never reach the clipping threshold can reset the hold. Equal-and-opposite stereo controls do not reset it, while mono, same-sign and over-canceling controls do. A clipping-only reset or a maximum taken independently across channels misses these observations.

The [early-tail record](measurements/2026-10-26-spiral-envelope-tail-identification.json) fits a common stereo threshold in a saturated square fixture. It uses only the interval before new post-source feedback can return. The renderer provides float32 diagnostic traces; the analyzer deliberately flattens their post-source threshold before fitting the original output, so it cannot inherit the proposed release curve. The preceding saturated source supplies the candidate feedback state, which remains an explicit assumption.

Both directions show the first threshold change at frame 96,320, after the source ends at 96,000. Its ratio is about 0.942726, consistent with the eleventh smoothed-input update providing a floor rather than a full one-decibel drop. Down's next changes are at 101,152 and 105,984: exactly 4,832 frames, or 151 internal blocks, apart. This distinguishes release-before-floor ordering and a `>150` counter from the earlier 150-block approximation. A common initial counter value of ten matches the checked activation phase. It does not establish a manufacturer pipeline or latency split.

The current empirical activity signal is the absolute stereo sum of the generated wet stream. Near-threshold controls bound its gate to approximately 0.000977602–0.000982641 times the candidate held envelope. The fixture uses the bracket midpoint. An exact `1/1024` hypothesis predicted that a control at ratio `3.88e-5` would reset the hold. Fresh captures at host blocks 32, 128 and 256 all contradicted that prediction. These three failed predictions remain in the report and make the identification CLI exit 1, even though all first-pass fits pass. The reference outputs are bit-identical across those host block sizes. The gate is a fitted model parameter, not an attributed manufacturer constant.

The rejected clipping-only, 150-block model lost six cases that had passed the previous checkpoint. The corrected research fixture keeps every previous passing case and fixes the original sparse Down tails and the Up stereo square fixture. Nevertheless, `down-blocks-64` in the attack stage still fails its complete render, and 69 other complete renders fail. Neither the improved case count nor the component fits justify moving this candidate into production yet. Exact activity/numerical behavior, the remaining Up feedback, Main/pitch mapping and the wider fidelity plan remain open.

## Reproduce

Use the [reference host and reviewed bypass calibration](../../docs/audio-matching.md). Capture the initial and structure stages with `tools.rmx_spiral_characterize`; those stages supply the earlier clipped impulse fixtures. Capture each new stage into a new directory:

```sh
uv run --locked python -m tools.rmx_spiral_core capture \
  --stage linear --host /path/to/Intel/RMXReferenceHost \
  --plugin /path/to/RMX-1000Plug-in.vst --session build/artifacts/research/core-linear
```

Repeat with `--stage peak-phase`, `--stage stereo-linear` and `--stage detector`, each with a separate session directory. These four recipes contain 20, 28, 10 and 36 captures respectively. `verify --stage STAGE --session DIRECTORY --report NEW.json` checks capture identity, hashes, exact input samples, static controls, BPM, tail and host block size against the recipe. It does not certify sonic matching.

```sh
uv run --locked python -m tools.rmx_spiral_core identify \
  --linear build/artifacts/research/core-linear \
  --peak-phase build/artifacts/research/core-peak-phase \
  --stereo-linear build/artifacts/research/core-stereo-linear \
  --initial build/artifacts/research/spiral-identification/initial \
  --structure build/artifacts/research/spiral-identification/structure \
  --calibration calibration-reviewed.json \
  --report build/artifacts/research/core-identification.json \
  --header build/artifacts/research/SpiralNeutralCalibration.h
```

The fitter uses only the project's locked NumPy dependency. The optional header is a new experiment artifact; it does not overwrite the committed calibration. To render the committed incomplete candidate:

```sh
cmake --build build --target rmx_core
c++ -std=c++20 -O2 -I include research/audio/experiments/spiral_neutral_probe.cpp \
  build/librmx_core.a -o build/spiral-neutral-probe
uv run --locked python -m tools.rmx_spiral_core compare \
  --case build/artifacts/research/spiral-identification/initial/up-probe-main-128 \
  --case build/artifacts/research/core-linear/down-dc-0.2-impulse-0.0001 \
  --renderer build/spiral-neutral-probe --calibration calibration-reviewed.json \
  --output build/artifacts/research/core-candidate
```

Both selected cases now pass; an Up DC-conditioned case still fails. Comparison applies only the independently reviewed 32-frame bypass offset, with no gain fit or wet alignment search. It checks whole output and separately subtracted wet output per channel. Silent channels use an absolute leakage check and carry no percentage similarity claim. Reports, output directories and optional headers must be new. Original recordings and plug-in binaries remain local under ignored research artifacts.

Capture `--stage long-clock` and `--stage probe-zero` into separate new session directories, then verify each with the same stage. These add one and two captures. Analyze the long clock with:

```sh
uv run --locked python -m tools.rmx_spiral_core clock \
  --session build/artifacts/research/core-long-clock \
  --renderer build/spiral-neutral-probe --calibration calibration-reviewed.json \
  --output build/artifacts/research/core-long-clock-analysis
```

`compare --session DIRECTORY` selects every captured Main-128, Sub2-zero, 120-BPM case in that directory. Repeat `--session` for the six characterization stages, four original core stages and new `probe-zero` stage to reproduce the 208-case sweep. Out-of-scope controls are listed separately in the report; they are not passes. `--case` remains available for explicit recordings. The long-clock command is a component analysis and cannot certify the complete effect.

For the envelope campaign, capture each stage into its own new directory using `tools.rmx_spiral_envelope capture --stage STAGE --session DIRECTORY --host HOST --plugin PLUGIN`, then use `verify` with the same stage/session and a new `--report`. Counts are memory 16, timing 25, level 7, after-tone 8, reset 9, reset-small 16, reset-edge 16, reset-fine 6, reset-validation 6, stereo-reset 5, boundary 8 and attack 13. Capture order does not carry state between cases.

```sh
uv run --locked python -m tools.rmx_spiral_envelope identify \
  --memory captures/memory --timing captures/timing --level captures/level \
  --after-tone captures/after-tone --reset captures/reset --reset-small captures/reset-small \
  --reset-edge captures/reset-edge --reset-fine captures/reset-fine \
  --reset-validation captures/reset-validation --stereo-reset captures/stereo-reset \
  --boundary captures/boundary --attack captures/attack \
  --components research/audio/measurements/2026-10-26-spiral-core-identification.json \
  --calibration calibration-reviewed.json --report build/artifacts/research/envelope.json
uv run --locked python -m tools.rmx_spiral_envelope tail \
  --case captures/nonlinearity/down-square --case captures/nonlinearity/up-square \
  --renderer build/spiral-neutral-probe \
  --components research/audio/measurements/2026-10-26-spiral-core-identification.json \
  --calibration calibration-reviewed.json --output build/artifacts/research/envelope-tail
```

The identifier intentionally returns 1 for the preserved rejected binary-gate prediction. The tail component command passes its declared fitting screen. Add all twelve envelope session directories to `tools.rmx_spiral_core compare` to reproduce the 343 complete renders; its aggregate result also remains a failure. Both analyzers run in the locked uv environment with NumPy and no SciPy installation. The optional seventh renderer argument writes new `pre.wav` and `limited.wav` diagnostics into a new trace directory; normal rendering does not allocate these trace buffers.
