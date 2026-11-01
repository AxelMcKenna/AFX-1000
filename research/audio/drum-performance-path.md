# Drums through the complete performance path

The 1 November 2026 pass compares the actual shared engine with RMX-1000 Plug-in 2.2.0 at 48 kHz. It covers moving Scene controls, all three Isolator modes, Release, effect switching, host tempo changes and drums mixed with synthetic external input. It does **not** establish a whole-device percentage or physical RMX-1000 equivalence.

The initial checkpoint and its source/binary bindings are in the [performance validation receipt](measurements/2026-11-01-performance-path-validation.json). The later [Scene-switch checkpoint](scene-switching.md) updates selection to 9/9 and the declared total to 43/54; its separate receipt binds the current model. These are ten-second programs with multiple pads, rolls or overdubs, varied callbacks, pitch and level. Each active program has a separately rendered control containing the same source and drum commands with the effects removed.

| Fresh family | Active programs passing every gate | Main remaining issue |
| --- | --- | --- |
| Scene Main/Sub 1 movement | 6/9 | Echo, HPF Echo and Crush movement |
| Scene plus moving Isolator bands | 9/9 | Wider independent routes, profiles and tempos remain outside this fixture |
| Release mid-pattern | 8/9 | Back Spin combined with Reverb Up |
| Scene selection and enable/disable | 9/9 | Arbitrary pairs, interrupted switches, Noise and wider profiles/tempos remain outside this fixture |
| Host tempo 120 → 137 → 91 BPM | 2/9 | Echo/filter delay geometry and Spiral outside manual 120 BPM |
| Source changes with external input | 9/9 | Wider material, levels and User settings |
| **Declared active programs** | **43/54** | Coverage count, not device accuracy |

All 54 matched drum/source controls pass, using the final boundary regression for the tempo family and complete prediction-WAV identity for the other families. All nine additional fresh tempo controls also pass. Reverb Up and Down are the two qualifying active tempo cases. The full-output HPF motion windows pass, but its effect-difference windows still fail; it remains unqualified. Earlier failed and interrupted campaigns retain their original verdicts.

## What changed and how it was identified

The baseline discovery pass qualified 5 of 18 active interaction programs. The corrected model qualified 12 of those same 18, then faced a separate 54-program fresh set. Reference captures follow frozen native predictions; no gain, lag or crop is fitted per case. Both sides discard the same predeclared first 32 frames. Every channel must satisfy 1% relative RMS error in the complete output, each one-second window and each control-event window. Reference-silent channels instead require absolute RMS error at or below 1e-8. The active-minus-matched-control signal faces the same gates, preventing the direct drum path from hiding a wrong effect.

**Filter motion.** A read-only, hash-pinned debugger observer measured the effective BPF/HPF/LPF Main control advancing one raw count every 16 samples. The engine now uses that motion clock and the final control target at each shared 32-frame boundary. Changing filter coefficients also translates the recorded input/output history into the new biquad state. Static coefficients retain their previous arithmetic. This improved the HPF whole output but did not qualify its smaller effect contribution.

**Echo time gestures.** Four echo returns have 160-sample send-weight ramps. Previously the renderer changed the weights of already recorded returns, incorrectly changing stored tails when Sub 1 moved. The corrected path weights new sends. Old unweighted samples are converted lazily as they are read, preserving previous static output bits and avoiding callback allocation or a bulk buffer rewrite. A regression test changes timing after the input ends and checks that existing tails are not rescaled.

**Source selection.** The reference has four independent linear 160-sample gains for selected and bypassed input/pad buses. These now run on the shared source clock, including a shared Isolator route. All nine fresh source-change programs pass, including drums mixed with a non-silent, asymmetric synthetic stereo source. Independent Scene/Isolator source selections and User routing are not covered by this result.

**Release return.** In Default mode, returning Release with Scene retention disabled bypasses the complete Scene contribution, including ringing returns. The engine carries that action on the common source clock. Ordinary Scene button-off still follows its existing tail behavior. Back Spin plus Reverb Up remains a visible failure, including excess audio in reference-silent windows.

**Host-synchronized overdub.** The factory command recorder is now eligible with a valid synchronized host, rather than falling back to the generic sequencer. A remaining missing hit was isolated by observing only our synthetic pattern command words, timing and suppression flags in the reference. The observer left all captured audio and auxiliary hashes unchanged. A native diagnostic build likewise reproduced the complete ordinary native WAV before its private sequence metadata was used.

The fault was a suppression flag attached to a future table slot. A host correction skipped that slot, leaving the flag alive until the next loop and suppressing a valid recorded hit. The measured unquantized flag applies to the next read boundary and clears there. Quantized handling remains separate. A unit test deliberately skips a read slot, then verifies replay on the following loop. The previously failing active/control pair and nine new tempo controls pass after this correction.

**AU/VST3 feedback.** A distinct wrapper check exposed Release's engine reset being overwritten by stale host controls on the next callback. Host parameter notifications are now consumed once using lock-free revision counters. Real-time processing retains the engine reset while message-thread host feedback is pending; offline processing publishes that feedback synchronously. The runtime probe checks Release return and explicit re-enable in both modes without dispatching the UI timer. This is a wrapper delivery fix, separate from Original fidelity qualification.

## What the switch observer found

A short reference control trace changes BPF Echo → Echo → BPF Echo. Requested and selected effects differ during a five-block fade-out. The common wet gain moves 1.0 → 0.8 → 0.6 → 0.4 → 0.2 → 0.0 in 32-frame blocks, then the newly selected processor initializes and fades in over another 160 samples. Complete ordinary and observed capture artifacts agree.

The subsequent [Scene-switch implementation](scene-switching.md) coordinates these gains, the selected-effect clock and private restarts. All nine regression programs and nine fresh timing holdouts pass every gate, with paired controls. Its documented scope excludes arbitrary switch pairs, interrupted changes, Noise and wider settings/tempos.

## Reproduction, validation and retention

[Performance fixture](../../tools/performance_path_probe.cpp) version 4 accepts non-silent stereo input and timestamped Scene, Isolator, source, Release and host-transport changes. Earlier fixture versions remain readable. The old drum fixture is preserved unchanged. The [campaign runner](../../tools/rmx_performance_path.py) verifies plugin identity, executable hashes, plan and input hashes, immediate parameter readbacks, explicit transport and complete render receipts. Optimized and ASAN/UBSAN complete WAVs must agree before the Original is rendered. A separate dot-product implementation checks the raw audio scores before deletion; gain, silence and one-sample-shift negatives must fail.

The [retained-energy auditor](../../tools/rmx_performance_path_audit.py) independently recomputes each published window verdict and paired aggregate from sums of squares, including gzip-compressed reports. It cannot reread deleted audio. The [preservation runner](../../tools/rmx_performance_path_preserve.py) compares 180 older manual-clock overdub, strip, mute/delete and quantize programs and replays 90 non-tempo fresh prediction hashes. A separate 53-program bridge covers older performance and input-only Release outputs. All pass. Another 37 short deterministic, resonant, Sidechain and Random Noise programs preserve their prior output bytes; these are preservation checks, not new long-duration statistical qualifications.

[Wrapper delivery](../../tools/rmx_performance_path_delivery.py) uses a distinct declared recipe: normalized controls and MIDI one-shots, with touch/roll/record events removed and the native prediction regenerated. Release cases additionally re-enable Scene after return. Complete decoded AU/VST3 samples are compared with native samples at fixed 32-frame latency and 1e-5 maximum/relative error gates. This does not qualify physical controller behavior or wrapper strip/overdub delivery.

All 108 performance delivery comparisons and 14 additional asymmetric-input Noise comparisons are sample-identical to native output. Each format passes 363 runtime checks, including Release return without UI dispatch, real-time re-enable using separate off/on callbacks and offline re-enable after host feedback. The host explicitly sets and reads back the AUv2 OfflineRender property; JUCE's generic host flag alone did not forward it. Failed preflight captures remain in the provenance archive.

The final checks pass 10 native suites, two ASAN/UBSAN suites, 11 Python tooling tests and all 16 firmware-host tests. The current firmware tree includes concurrent integration repairs; its former factory-silence failure no longer reproduces. Engine object size is 50,688 bytes, within the 65,536-byte limit, with unchanged 30,100,112-byte prepared audio-buffer storage. Allocation guards pass.

All capture workflows run serially, enforce a 512 MiB temporary-file budget and delete audio before proceeding. Retained artifacts contain numerical diagnostics, hashes, compact plans and verdicts only. No reference assembly or captured audio is distributed. The pause marker stays in place. Only the validated current playable preview is retained.

Use `uv run --locked python -m tools.rmx_performance_path --help`, `uv run --locked python -m tools.rmx_performance_path_audit --help`, `uv run --locked python -m tools.rmx_performance_path_preserve --help` and `uv run --locked python -m tools.rmx_performance_path_delivery --help` for the reproducible entry points. The [unified observer](../../tools/rmx_performance_path_observe.py) reproduces the selector and pattern traces with `--mode selector` or `--mode pattern`; supply the explicit pinned Intel host and Original bundle. `--expected-output-sha256` additionally pins the ordinary capture to a prior program. Source manifests and reachable model commits distinguish baseline, intermediate and final runs; a passing replay transfers only its original verdict, including retained failures.
