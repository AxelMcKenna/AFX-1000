# Continuous Noise measurements within the capture budget

Completed 4 November 2026. **All three previously inconclusive programs qualify** under the existing statistical margins. This required longer measurements and no production DSP change.

| Program | Stationary duration | Overall / full profile | Early / late profiles | Required stationarity |
| --- | --- | --- | --- | --- |
| Wild Random / Sub2 223 | 7,140 seconds | Pass / Pass | Pass / Pass | Diagnostic; also passes |
| Mild Sidechain / low bursts | 7,140 seconds | Pass / Pass | Pass / Pass | Both sources pass |
| Default Sidechain / asymmetric stereo | 7,140 seconds | Pass / Pass | Pass / Pass | Both sources pass |

The [validation receipt](measurements/2026-11-03-noise-continuous-validation.json), [window report](measurements/2026-11-03-noise-continuous-report.json.gz), [original declaration](measurements/2026-11-03-noise-continuous-plan.json) and [independent audit](measurements/2026-11-03-noise-continuous-audit.json.gz) bind the measurements. The independent arithmetic agrees within 3.7e-16. All 18 complete retained native/sanitizer WAV pairs agree byte-for-byte. The [capture bridge](measurements/2026-11-03-noise-continuous-bridge.json.gz) passes all three presets and cleanup/invalid-window guards.

All 166,137 observed Random targets match the actual native and sanitizer generators. Ordinary and observed final-window audio and every required auxiliary artifact agree. The first 1,194-second Random Original WAV repeats its earlier published hash. All overlapping 1,190-second Random and 600-second Sidechain powers/profiles/exposures repeat exactly in the [prefix audit](measurements/2026-11-03-noise-continuous-prefix-repeatability.json.gz). The earlier inconclusive verdicts are not rewritten or pooled into a larger sample count.

The old Wild/Random early-profile level bound exceeded the 0.1 dB limit; the longer run's worst early conditional level bound is about 0.06062 dB. The low-burst overall level bound is about 0.06739 dB. These are statistical level-interval bounds, not percentages of perceived similarity. All declared Random and Sidechain presets now have scoped qualifications across their respective published cohorts; previously qualified programs retain their earlier durations and limits.

The preceding [Random](noise-random.md) checkpoint left Wild/223's early high-control-bin right-channel level inconclusive. The [Sidechain](noise-sidechain.md) checkpoint left the low-burst and asymmetric-stereo programs inconclusive. Their original verdicts remain unchanged. A finite confidence interval crossing an equivalence margin does not identify a DSP fault by itself.

This study declares **7,140 stationary seconds per preset**, after the same four-second warmup, before collecting the new data. It uses the same three User presets, 48 kHz/manual 120 BPM and Original RMX-1000 Plug-in 2.2.0. Earlier, overlapping shorter captures are not pooled with this study. The reference executable remains hash-pinned; production DSP and the signed playable preview are unchanged.

A longer deterministic render repeats the earlier prefix. This is an extended comparison of the same programs, rather than wholly unseen or independent repetitions. The observed debugger render is an identity check and contributes no additional statistical exposure.

## Collecting a longer run without retaining larger WAVs

The [native fixture](../../tools/noise_user_probe.cpp), protocol version 5, processes one uninterrupted run and hands off six adjacent windows. It closes a WAV before announcing it, then waits for the [consumer](../../tools/noise_window_batch.py) to summarize and delete that file before continuing. An acknowledgement while the WAV still exists is rejected. Native and ASAN/UBSAN runs use the same callback sequence and must produce identical complete WAV bytes for every retained window. All predictions precede the new Original captures.

The first file includes the four-second warmup and 1,190 stationary seconds. Each later file includes its preceding 128 frames and 1,190 new stationary seconds. Only the new stationary interval contributes to two-second powers and stereo correlation. The 128-frame prefix supplies the Hann window that crosses the boundary; it is counted once in the conditional profiles. No effect state is restarted at a native window boundary.

The reference host's optional `render_window` processes the complete prefix from a fresh, identically initialized instance and saves the requested interval. Its transport and callbacks advance through all preceding samples. A one-second synthetic input repeats without splitting audio callbacks, allowing the longer Sidechain run to stay within the same 512 MiB disk budget. Every capture receipt records processed frames, captured frames, global start and input repetition explicitly. Ordinary plans retain their existing behavior.

The [capture bridge](../../tools/rmx_noise_window_bridge.py) checks all three presets against the old native renderer and unchanged reference host. It requires complete ordinary audio and auxiliary-file identity, repeated versus explicitly expanded input identity, and sample-bit identity between saved windows and non-block-aligned ordinary crops. Final state, parameter logs and inventory must also agree. Native and sanitizer batches are compared with complete ordinary runs. Invalid windows and a consumer that retains its WAV must be rejected.

The statistics tests separately compare an ordinary 80-second stationary analysis with two adjacent windows. Two-second powers, every conditional profile power and FFT exposure count agree exactly, including the boundary FFT; combined correlation agrees to numerical precision. Random labels come from the actual control probe with global frame positions.

## Keeping the acceptance rules fixed

The [collector](../../tools/rmx_noise_window_stream.py) writes a declaration containing the horizon, presets, source/binary hashes and margins before capture. Whole-run meaningful bands retain the 0.5 dB margin, total level 0.1 dB, stereo correlation 0.02 and meaningful-band floor −40 dB. Existing two-lag HAC arithmetic and its 3.0 uncertainty multiplier are unchanged. Full, early-third and late-third conditional profiles must all pass.

Sidechain retains its independent-power overall screen and each source's early/late stationarity gates. Random retains the ratio-of-mean-powers estimator with paired covariance, justified by observing the complete shared modulation-target trajectory; it also requires full/early/late overall comparisons. Its nonperiodic-trajectory self-stationarity result remains a diagnostic. Independent white-noise excitation is retained in both cases. No gain adjustment is fitted to an observed difference.

The compact Random observer records only computed float control targets. It never reads PRNG words or audio buffers, and writes no DSP state. Ordinary and observed audio, plan, state, parameter-log and inventory hashes must match. The actual default native and sanitizer control probes must reproduce every observed target. A matching control sequence does not imply identical stochastic audio samples.

The [independent auditor](../../tools/rmx_noise_window_audit.py) uses the existing separate sums/einsum implementations to recompute overall and conditional intervals, masks, subwindow verdicts, stationarity and aggregate qualification. It checks all six capture spans and receipts, exact FFT exposure coverage and default target replay. Both whole and conditional 3 dB gain negatives must be rejected. A full engineering screen is distinct from a listening or whole-device accuracy claim.

## Reproduction and retention

Build `rmx_noise_user_probe` and `rmx_noise_random_probe` in optimized and ASAN/UBSAN configurations. Build the reference host separately for the architecture required by the installed Original. Run the bridge first with the prior native renderer and reference host, then `uv run --locked python -m tools.rmx_noise_window_stream --help` for explicit input paths. `--case` can select a declared preset; the horizon is fixed and is not extended repeatedly until a pass appears. The auditor accepts retained compressed reports and their matching declaration.

Retain compressed powers, plans, receipts, scalar target values, verdicts and source manifests. Delete raw audio serially and keep the existing signed playable preview when production is unchanged. The pause marker and canonical reference installation remain untouched.

The three compressed power files total 17,436,135 bytes. Peak temporary capture storage was 458,939,414 bytes, below 512 MiB. All 76 production-source hashes and signed preview files match the preceding performance checkpoint, so no replacement app is generated. The current playable bundles remain in `build/live-engine-preview-20261103-motion`. Twelve tooling tests, native/sanitizer Scene suites and the three-preset transport bridge pass.

The first dry-control preflight was rejected because amount zero still produces Noise with the Random preset's nonzero minimum. The separate dry control now declares a zero minimum; the measured Random preset retains its original minimum. An initial prefix-replay attempt was stopped to remove repeated native startup work; no qualification was accepted from it. Its horizon was preserved in the continuous native rerun. These attempts are provenance, not passing evidence.

An external temporary template disappeared during the first Sidechain run. Its incomplete case was discarded. The fully completed Random case was retained only after checking its complete source and binary bindings. A fresh plug-in instance, configured through normal public parameter setters, exported the exact original 257-byte template with matching SHA256. Both Sidechain cases were then rerun at the same declared horizon, margins, presets and source/binary hashes using a task-owned copy. The [provenance](measurements/2026-11-03-noise-continuous-provenance.json.gz) retains the interruption, exact recovery and completed-case attestation.

Captures use measurement commit `1c73ab6f`. The subsequent input-snapshot fix `2b3557b7` reads, validates and hashes template bytes once at startup. A regression deletes the source file after loading it, then requires subsequent prepared state and plans to remain identical. This fixes the interrupted workflow without changing the captured DSP or statistical calculations.

This work addresses three declared stochastic Noise programs. Dynamic controls/mode changes, arbitrary material and independent routes, other settings/rates/tempos, sampling, overload, listening and physical hardware require separate coverage.
