# Spiral core identification, 26 October 2026

The original 2.2.0 plug-in now has reproducible experiments for separating its linked level measurement, clipping, linear filters and internal repeat clock. The [component identification](measurements/2026-10-26-spiral-core-identification.json) records 42 selected reference captures and verification of 94 input/control recipes. These are software observations at Default, Main raw 128, Sub2 zero, 48 kHz and 120 BPM unless explicitly labeled otherwise. No manufacturer implementation or recorded audio is included in the source tree.

The experimental complete model **fails** the [full-render comparison](measurements/2026-10-26-spiral-core-prototype-48k.json). It is a research fixture, separate from the production engine. Its partial successes do not establish full Spiral or device similarity.

## What the new experiments establish

The stereo level measurement operates in groups of 32 input frames. A right-channel pulse is compensated so the instantaneous stereo sum reaches the same peak at different positions. Moving that pulse anywhere within the first group leaves the complete left output bit-identical. Positions in later groups move its response accordingly. Host blocks of 32, 128 and 256 produce identical checked recordings, establishing that this grouping belongs to the reference processing rather than the capture host.

Equal and opposite tones produce zero wet output. Changing the right input, including adding positive or negative DC, changes the left wet level substantially. The peak measurement is therefore linked across channels. Quiet differential pulses after a common high-level preconditioning signal leave the unchanged left response bit-identical across same/opposite/asymmetric right pulses. A mono differential pulse creates no right-channel difference. These quiet tests rule out direct linear crossfeed as an explanation of the observed level coupling; they do not establish nonlinear channel independence.

Holding the stereo sum high while sending much smaller left impulses exposes a linear first pass. A tenfold impulse change at two DC levels gives the same normalized response within roughly 0.00003% RMS error. Identification windows end before the next internal repeat: 2,048 frames compared with approximately 2,496 frames for Up and 12,144 for Down. DC is an offline diagnostic fixture, not a proposed hardware stimulus.

The first-pass clipping response is explained by a 12 kHz, Q 0.707 input low-pass followed by clipping. Joint fits of quiet linear and two clipped impulse cases have normalized errors below 0.00003%. A 32-tap output-shaping calibration and three slow real filter poles reproduce those windows. Their placement around a complete nonlinear feedback processor is not established by these fits alone.

Quiet internal repeats identify an additional 12.1 kHz, Q approximately 0.7 low-pass and two high-pass sections. Their small-signal loop gains are approximately 1.5 for Up and 1.2 for Down. First-return component fits have errors below 0.00005%. Fractional repeat positions drift by approximately two parts per million even at the neutral pitch setting. Repeated quiet impulses distinguish that drift from a constant fractional delay. The record retains the measured fractions rather than attributing the drift to an unverified implementation detail.

The measured first-block threshold is about `0.002673797 * peak(abs(L+R))`. Interpreting this as half a smoothed envelope suggests a block smoothing coefficient near 0.005347594. That separation is a model convention; the first-block fit alone identifies their product. Source release, feedback normalization, clipping placement and their interaction remain unresolved.

## A deliberately incomplete model

[spiral_neutral_probe.cpp](experiments/spiral_neutral_probe.cpp) combines these components with a candidate peak-hold envelope and feedback arrangement. Its [calibration header](experiments/SpiralNeutralCalibration.h) is generated from the numerical identification. It accepts only Main raw 128, neutral Sub2, 48 kHz and 120 BPM; Sub1 selects the separately validated outer return.

Four complete mono/square tone cases pass the declared one-percent unscaled per-channel RMS screen, including their tails. The largest checked wet error among them is about 0.017%. Six complete sparse-impulse, DC-conditioned and stereo broadband cases fail. Some fail by more than 100% wet relative RMS error. Those failures remain in the committed report and the comparison CLI returns exit code 1. A good first pass or periodic tone cannot substitute for those complete recordings.

The failed cubic-feedback and extra-clipping experiments remain local diagnostics, not alternate production algorithms. The next identification step must explain the sparse-tail and broadband failures while preserving the already measured input, timing and quiet linear responses. Other Main positions, nonzero pitch, gestures, User settings, overload and hardware require separate validation.

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

Those complete cases are expected to fail. Comparison applies only the independently reviewed 32-frame bypass offset, with no gain fit or wet alignment search. It checks whole output and separately subtracted wet output per channel. Silent channels use an absolute leakage check and carry no percentage similarity claim. Reports, output directories and optional headers must be new. Original recordings and plug-in binaries remain local under ignored research artifacts.
