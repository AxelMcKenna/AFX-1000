# Matching the live Noise controls to the reference probes

1 November 2026. The live Engine and Noise control probes now call the same production functions, compiled with floating-point contraction disabled. All nine declared Triangle/Saw/Square audio programs qualify after output-preservation bridges and fresh checks of the two changed programs. Sidechain retains one qualified audio program out of three, with its two inconclusive results unchanged.

Subsequent work reconstructs [Random modulation](noise-random.md). This document preserves the preceding checkpoint's measurements and scope.

The [validation receipt](measurements/2026-11-01-noise-control-fp-validation.json) links the production-control audit, whole-WAV bridges, fresh numerical powers, independent arithmetic and signed-format delivery. Earlier [modulation](noise-modulation.md) and [Sidechain](noise-sidechain.md) reports retain their original verdicts.

## The compiler discrepancy

The earlier standalone control probes were compiled with `-ffp-contract=off` and matched the Original's control streams exactly. Final inspection found that the live Scene translation unit could emit fused multiply/add/subtract instructions for the same inline header functions. Matching a standalone model had therefore not established identical arithmetic in the production control generator.

One affected expression computes the period from the smoothed Sub2 control. At visible223, after smoothing to220, the separate float32 operations produce2057.14208984375 samples, while the fused expression produces2057.142333984375. A fused operation also appeared in the Sidechain gate's rise expression. Small rounding differences matter when controls accumulate over many cycles and select integer filter positions on16-sample edges.

Both [control functions](../../src/core/NoiseModulator.cpp) are now out of line in one production translation unit. Root and firmware CMake builds compile it with contraction disabled. CMake's `rmx_noise_motion_probe` and `rmx_noise_sidechain_probe` targets link `rmx_core`; their control arithmetic is supplied by that object, rather than another header-generated copy. Filter coefficients, excitation, gains, return processing and qualification margins are unchanged.

The [production-control auditor](../../tools/audio/noise/rmx_noise_control_fp_audit.py) verifies that the function bodies were moved without changing their source arithmetic, checks the explicit compiler flag and absence of fused operations in the built object, and confirms that Scene refers to those shared functions. It regenerates all24 prior deterministic streams and seven Sidechain streams through native and sanitizer builds. All31 complete streams match their retained Original hashes:2,634,208 modulation values, including22 previously frozen prospective streams. Detector and threshold values in the Sidechain records match as well. The source/binary/object hashes are retained; raw observations remain deleted.

To reproduce the shared build, use `cmake --build build/core --target rmx_noise_motion_probe rmx_noise_sidechain_probe` after configuring the checkout, and build those targets in the sanitizer configuration too. `uv run --locked python -m tools.audio.noise.rmx_noise_control_fp_audit --help` lists the observation reports, baseline commit, library and object files needed for replay. The audit's baseline is the preceding Sidechain commit, so the old inline bodies remain inspectable in Git.

## Rechecking the audio

The three-second bridge checks35 programs against the preceding Sidechain engine.34 complete WAVs are unchanged; Wild/Saw changes. Longer checks are retained separately: seven of nine deterministic600-second outputs, all three Sidechain600-second outputs, and all three previously qualified1196-second deterministic extensions retain complete WAV identity. The two deterministic programs whose600-second outputs change receive fresh Original comparisons.

Default/Triangle at main173/Sub2=223 passes every600-second gate. Wild/Saw passes overall and full-profile checks at600 seconds but retains inconclusive profile subwindows, so that aggregate result remains false. Its1196-second extension passes every gate. Combining these fresh results with the byte-preserved prior qualified evidence qualifies all nine declared deterministic programs. Overlapping captures are not pooled or relabeled as independent observations.

The Wild/Saw correction has a particularly useful controlled comparison. The entire1196-second Original WAV is identical to the earlier reference, and every retained profile label is identical. The preceding live renderer also reproduces its old complete candidate WAV. Only the candidate control implementation changes. In the formerly inconclusive late0–500Hz band of the highest control bin:

| Stage | Left paired log-power difference | Right paired log-power difference | Late-profile verdict |
| --- | --- | --- | --- |
| Earlier live arithmetic |+0.584dB, interval[+0.431,+0.737] |+0.565dB, interval[+0.418,+0.712] | Inconclusive |
| Shared operation-ordered core |+0.049dB, interval[−0.105,+0.203] |+0.017dB, interval[−0.132,+0.166] | Pass |

The0.5dB band margin,0.1dB level margin, meaningful-band floor, HAC correction and uncertainty multiplier stay fixed. The [correction receipt](measurements/2026-11-01-noise-control-fp-weak-band-correction.json) binds the same reference WAV, full label stream, old-candidate reproduction and numerical powers. The independent auditor recomputes all new intervals and verdicts. This closes that declared Wild/Saw discrepancy without changing a gain or fitting another filter curve.

The Sidechain audio data is unchanged through the correction: its three complete600-second candidate WAVs match the preceding checkpoint. One declared step-input program qualifies; low-burst and asymmetric programs remain inconclusive. Complete Sidechain control agreement does not upgrade those audio verdicts. Random remains on its preceding audio path.

## Delivery and scope

The replacement signed AU/VST3 bundles reproduce native decoded samples exactly in all34 non-silent delivery comparisons: Default, the nine deterministic and three Sidechain programs with low input in both formats, plus Default and the three Sidechain programs with asymmetric input. Each format passes359 runtime checks. Source-report qualification flags in the delivery data remain historical context; current Original-fidelity decisions use the qualification map in the final validation receipt.

Eight affected native groups, two sanitizer groups and seven Python tooling tests pass, including the Sidechain callback/reset allocation guard. The engine object remains50,368 bytes and prepared audio buffers30,100,112 bytes. Firmware-host remains15/16 with the inherited `full_integration: Full engine factory path is silent` failure. Both host and firmware source lists include the new production file and its contraction flag.

Audio is generated one case at a time, under512MiB. The1196-second silent-input checks retain one whole WAV; Sidechain keeps one synthetic input and one output. All raw audio and transient observations are removed, while compressed powers and small receipts remain. Only the current signed playable preview is kept.

These results cover declared fixed User programs at48k/120BPM, silent input for deterministic modulation and specified synthetic inputs for Sidechain. Random, the two inconclusive Sidechain programs, arbitrary music, changing controls, other rates/tempos, independent source combinations and physical hardware still require separate work. Nine qualifying programs do not establish99% accuracy across the device.
