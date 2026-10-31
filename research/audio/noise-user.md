# User Noise widths and bounded reference validation

30 October 2026. Noise now uses independent stereo excitation and the reconstructed filter for Mild, Default and Wild widths at48k. Three fresh User presets pass600-second level/spectrum equivalence, stereo correlation and early/late-third equivalence. A corrected180-second Normal-width preset also passes those screens. These are statistical response checks, not sample-null or perceptual99% claims.

The fresh Default control passes its overall600-second level/spectrum comparison. Its stricter early/late-third comparisons remain **inconclusive** in both Original and candidate; the report keeps that aggregate qualification false. Four complete Default renders are byte-identical to the preceding engine, preserving the earlier Default behavior.

Detailed small reports and compressed two-second power summaries are linked from the [validation receipt](measurements/2026-10-30-gesture-noise-validation.json). No new raw audio is retained.

## Reference setup and the mapping correction

The Original's public RSD state loader requires `SceneFx/Lock` and all six Noise fields when that group is supplied. Silent state-load checks confirmed exact retention of the generated customization before longer comparisons. The checker also distinguishes the requested JSON double from the float delivered to the plug-in, allowing only decimal serialization error in the returned float. Incorrect requested values and incorrect readbacks remain rejected.

The Original popup order is Default/Mild/Wild, while the project uses Mild/Default/Wild. The RSD adapter therefore maps project choices0/1/2 to Original1/0/2. Initial comparisons with the wrong order are rejected setup evidence, not fidelity baselines.

The previous custom-width fallback generated mono noise and had the wrong response. Retained powers from that candidate, paired with the correctly mapped Mild Original, establish a failed baseline. The corrected candidate passes the corresponding overall statistical screen and preserves independent stereo output.

## Filter reconstruction

A read-only [observer](experiments/noise_coefficients_observer.py) sampled steady controls, two biquad coefficient sets and feedback values at two main-knob positions for Default and all three Original popup choices. All eight observed captures retained identical audio, plan, before/after state, parameter log and final inventory compared with ordinary captures.

For unmodulated Noise, the Original advances the visible main control by50 and clamps at255 before deriving its band edges. Each width has its own measured edge trajectories. A bilinear band-pass transform followed by the observed feedback law reproduces the eight coefficient records within4e-8, with exact float feedback values.

The project implements that filter as a third-order recurrence. The fitted Default response remains unchanged. For Mild/Wild, the new numerator is scaled relative to the Default band-pass numerator to retain the previously measured excitation/output-level law. The generator is the project's own independent stereo generator; no manufacturer noise generator, recorded source or binary is embedded.

The fresh presets change main position, level range, Sub1 position and callback length. They were rendered and hashed before their corresponding Original captures. Complete optimized/ASAN WAV identity is required before statistical comparison. AU and VST3 each deliver the Default control and all three qualified fresh User presets byte-identically to the native engine, with latency32; each format also passes359 runtime checks. Wrapper delivery is separate from Original fidelity.

## Statistics and retention

The unchanged statistical screen uses two-second Hann-window band powers, a conservative3.0 uncertainty multiplier with short HAC correction,0.5dB band and0.1dB overall-level margins, and the existing -40dB meaningful-band floor. Stereo correlation must agree within0.02. Qualification also requires early/late-third equivalence; an inconclusive result is not relabeled as a pass.

[`rmx_noise_stream.py`](../../tools/rmx_noise_stream.py) saves block powers and correlations, then deletes the native, sanitizer and Original WAVs. This preserves sufficient information for these stationary screens, but does not preserve waveform or transient information. The [independent auditor](../../tools/rmx_noise_power_audit.py) recomputes every interval and verdict using separate float64 moment arithmetic. A3dB gain error is rejected.

The runner enforces a512MiB temporary-data ceiling and removes each case directory before continuing. The longest tests peaked at443MiB. The drum replay used11MiB, and its temporary audio was also deleted. See the [artifact policy](artifact-retention.md).

## Remaining scope

These tests cover static widths and the declared custom minimum/maximum levels with Sub2 at zero,48k and120BPM. Modulation/resonance modes, changing User settings while sounding, other rates/tempos, all setting combinations, listening judgments and physical hardware remain unqualified. Other advanced Scene/Isolator settings still need their own reference campaigns.
