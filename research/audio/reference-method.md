# How the reference audio checks work

The check is an automated A/B experiment: give Pioneer's original RMX-1000 software and our independently implemented processor the same stereo samples and timed controls, record both outputs, then measure their difference. This guide explains the method behind the Reverb Down investigation. The [chronological research notes](reverb-down-motion.md) retain the discoveries, failed hypotheses and numeric reports.

At source checkpoint `9350b7b`, the standalone factory Default Down model passes 176 complete renders at 48 kHz and 120 BPM. That count includes development cases, repeated baselines, bypass probes and deliberately silent wet transitions. Only the last eight were newly captured after freezing that final candidate. It is not 176 blind tests, a listening score, or evidence that the whole device is 99% accurate.

## Establish the reference

The [offline reference host](../../tools/audio_plugin_render.cpp) loads the separately acquired original **RMX-1000 Plug-in 2.2.0**, checks its identity, and renders without a DAW's extra routing or effects. Its [VST2 adapter](../../tools/legacy_vst2_host.h) uses the public plug-in interface; the project does not incorporate the original DSP binary. The Intel reference host runs the original Intel plug-in locally.

Each capture keeps an input WAV, the requested settings and event plan, sample rate, tempo, callback size, original output, parameter readbacks, state snapshots, and a receipt containing hashes. Readback checks distinguish an accepted control event from a request the plug-in ignored. Audits recheck the files against the recipe and receipt rather than trusting a filename or a green summary.

Original binaries, large recordings and debugger artifacts stay in ignored `build/artifacts/research/`. The repository records our code, measured numeric facts and hashes. Reproducing the original side requires acquiring the original plug-in separately; our project plug-in cannot substitute for it.

## Design signals that separate causes

An impulse reveals delays, reflections and decay. Separate left/right impulses expose cross-channel paths. Seeded stereo noise, tones and chirps exercise a broad spectrum. Input gaps reveal a reverb tail without continuous dry audio masking it. Long tails expose slow state and feedback errors. Audio from frame zero tests cold startup, which a silent pre-roll would hide.

First hold controls still to identify geometry, filters and coefficient maps. Then move one control, reverse it before settling, change several controls together, and switch the effect on and off. Repeat with different callback sizes and events inside a callback. Source generators and seeds are stored in [the capture tool](../../tools/rmx_reverb_motion.py); predictions hash the actual float32 source samples as well as their recipes.

The Down model developed from a five-pair cross-coupled comb network, all-pass stages, input/output filters and measured static maps. Moving controls needed additional state machines: input gating and room controls use different clocks, and callback buffering affects physical output timing. Static impulse agreement alone missed these behaviors.

This was not exclusively black-box identification. Inspection of locally installed original binary symbols/control flow, followed by read-only LLDB scalar observations, helped identify control and startup state rules. Those observations are disclosed in the research notes. Debugger-run audio was checked against the original recording by hash. The candidate code was independently written; original binaries, instruction listings and raw debugger output are not distributed. Waveform comparisons, rather than an inspected state value alone, remain the acceptance evidence.

## Fix the comparison before judging the result

Independent bypass calibration establishes a nominal **32-frame** offset. The motion comparison crops 32 frames from each output; it does not search the wet audio for a better offset or fit a gain. Small and partial callbacks can change the original's actual physical timing. The model must generate that behavior causally; the comparison does not realign each case to conceal it.

For each channel, the relative error is:

```text
sqrt(sum((candidate - reference)^2) / sum(reference^2))
```

Every required screen must be at most **0.01 (1%)**. If the sum of squared reference samples is at most `1e-20`, the absolute error RMS must instead be at most `1e-8`. These rules are implemented by [`screen`](../../tools/rmx_filter_match.py). Channels are checked separately.

Checks cover the whole output, an estimated wet signal, the post-input tail, windows around every control event, and applicable activation/startup windows. Separate windows prevent a short error from disappearing in a long average. The estimated wet comparison subtracts the **candidate-predicted dry trace from both outputs**. That is useful but is not an independently recorded reference wet stem. At the 176-case checkpoint, 49 non-silent, pre-wet prefixes of 12,000 samples each match original output, candidate output and dry trace bit for bit; this independently checks dry subtraction over those prefixes only.

A 1% waveform-error threshold is an engineering acceptance rule. It does not translate directly to “99% perceptually identical,” and says nothing by itself about untested effects, settings or hardware.

## Freeze, capture, then keep the failures

Before a prospective set, `predict-motion` saves source/model/calibration/renderer hashes, exact source-sample hashes, settings, event frames, callback sizes, tail durations and the expected result. Capture refuses a changed binding. New original recordings are then made with that frozen candidate. Previous development recordings become regressions, not fresh validation of a later fix.

When a set fails, retain its prediction, failed report and source checkpoint, explain the correction, and use a further new set. For example, the second startup set passed six of eight cases. A one-float32-step dry-gain difference caused the two failures in direct-only windows. That report remains at source checkpoint `d2db16d`. After the arithmetic correction, a third frozen set passed all eight. Neither the limit nor the energy floor was relaxed.

## Audit the experiment and the implementation

The [auditor](../../tools/rmx_reverb_motion_audit.py) verifies recipes, receipts, auxiliary hashes, immediate/final control readbacks, candidate outputs, dry traces and schedules. Negative controls change source samples, controls, event times, callback size or duration and must be rejected. A bypass test rejects offsets 0, 31 and 33. Causal-prefix checks change later input/controls and require earlier output to stay identical.

Sanitizer builds and allocation/resource checks address implementation defects separately from sound error. Historical startup audits explicitly disclose that their linked WAV library was not rebuilt with sanitizers. A clean sanitizer run alone cannot turn a failed audio comparison into a pass or prove a microcontroller meets its callback deadline.

## Reproduce the current processor

From the repository root:

```sh
uv sync --locked
cmake -S . -B build/reference-method -DCMAKE_BUILD_TYPE=Release \
  -DRMX_BUILD_TESTS=ON -DRMX_BUILD_PLUGINS=OFF -DRMX_BUILD_REFERENCE_HOST=OFF
cmake --build build/reference-method --target rmx_reverb_down_probe rmx_reverb_down_tests
ctest --test-dir build/reference-method -R '^reverb_down$' --output-on-failure
uv run --locked python -m tools.rmx_reverb_motion --help
uv run --locked python -m tools.rmx_reverb_motion_audit --help
```

For reference comparisons, also prepare the original plug-in, the compatible Intel reference host and reviewed bypass calibration. The sequence is `predict-motion`, `capture --prediction`, `compare`, then the audit. Every report/session/output destination must be new. Use `--gate faded --cutoff-position post --gain-position read --quantum 32 --candidate-latency 32 --level-position output --coefficient-ramp 0 --ramp-components startup --decay-slew 0` for the current processor. Historical experimental modes require their recorded Git source checkpoints; current source hashes will intentionally differ.

The reusable implementation is [`CalibratedReverbDown`](../../include/rmx/CalibratedReverbDown.h), with [DSP and buffering here](../../src/core/ReverbDown.cpp). Its fixture harness uses that same class. Connecting it to the live Engine, validating the complete routing/callback path, and extending coverage to other profiles, sample rates, tempos, listening and physical hardware remain separate work. Passing this scoped matrix does not complete the full sound-matching goal.

The [bounded-processor checkpoint](measurements/2026-10-27-reverb-down-production-validation-48k.json) extends the example to **184/184**: all 176 earlier audio/dry traces stay byte-identical, then eight new recordings pass after a fresh freeze at larger callback sizes. Its [audit](measurements/2026-10-27-reverb-down-production-audit.json) includes a fully rebuilt sanitizer core/WAV/harness, and [resource checks](measurements/2026-10-27-reverb-down-production-resources.json) record bounded storage and zero instrumented callback allocation requests. These implementation checks support integration; the live Engine has not been connected to this processor yet.
