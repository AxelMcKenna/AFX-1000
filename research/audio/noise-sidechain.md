# Noise Sidechain detector and cutoff motion

1 November 2026. Noise Sidechain now drives the reconstructed moving filter from the shared low-frequency detector. Its preceding live path used an input envelope to modulate output amplitude. Random retains its preceding audio path. This is a scoped software-reference checkpoint, with no whole-device or perceptual accuracy percentage.

The later [continuous study](noise-continuous.md), completed on 4 November, qualifies the previously inconclusive low-burst and asymmetric programs over 7,140 stationary seconds each. All three declared Sidechain presets now have scoped qualifications across the published cohorts; the earlier Wild/steps result retains its 600-second scope. The following historical results keep their original verdicts.

The [validation receipt](measurements/2026-11-01-noise-sidechain-validation.json) links the complete-control audit, failed detector hypothesis, numerical powers, independent arithmetic, preserved outputs and signed-format delivery checks. The earlier [deterministic modulation checkpoint](noise-modulation.md) remains separate evidence.

The subsequent [production-arithmetic correction](noise-control-fp.md) makes the live Engine and probes share contraction-disabled control functions. All three Sidechain600-second outputs remain byte-identical, preserving this checkpoint's one qualified and two inconclusive audio results. It also closes the preceding deterministic Wild/Saw discrepancy.

## Finding the detector

The Original computes Sidechain from the low band of the same detector used by Gate/Drive. The existing [Gate/Drive reconstruction](../../src/core/GateDrive.cpp) already supplies its cascaded low-pass sections, per-channel histories, maximum absolute stereo magnitude, rolling peak history and delayed adaptive threshold. The new optional detector output is extracted before Gate/Drive changes its audio. It does not allocate another filter or audio buffer.

An initial mapping selected the high band. Controlled high/low bursts rejected it, with maximum driver errors around0.29. All five rejected comparisons remain in the discovery report. Replaying the envelope using the actually observed driver still gives zero error in each case. Following the detector's three output bands identifies the correct low-band input and threshold; fresh complete-stream comparisons verify that correction rather than relying on an address interpretation.

The [read-only observer](experiments/noise_sidechain_observer.py) temporarily records each call's scalar threshold,32 detector values and32 modulation values. It never reads random-generator state. Ordinary and observed runs must have identical output WAV, plan, before/after state, parameter log and final inventory hashes. All audio and temporary driver/control records are deleted after comparison.

## Reconstructing the envelope

For visible Sub2, the smoothed raw control advances one count per sample toward `max(raw - 3, 0)`, bounded to0..252. Sidechain depth is that value divided by252. Unlike Triangle/Saw/Square, it does not reach full depth at visible43.

The adaptive threshold moves toward a changed target over five32-frame blocks, stepping by `(newTarget - oldTarget) * 0.00625` each sample. The first envelope takes an immediate upward peak and decays by approximately0.999667823 per sample. The gate rises toward one with coefficient0.002443081 while the peak exceeds `threshold * 0.413569748`; otherwise it decays by0.999620557. Values below1e-10 are cleared at block end. The code preserves the observed float32 operation order and multiplies the resulting gate by Sidechain depth.

The resulting control moves cutoff with the existing `clamp(main + trunc((1 - control) * 50), 0, 255)` law and16-sample coefficient cadence. The shared Engine provides the detector on its32-frame clock, including the measured Noise startup block. Direct Scene callers without that shared detector retain their prior fallback. Independently selected Scene/Isolator sources, pad-driven detection and routing changes are outside this checkpoint's reference coverage.

Six fresh one-second synthetic programs cover silence, low and high bursts, a right-only burst, steps and asymmetric stereo, with Sub2 at4,29,117,201,223 and255. Native and sanitizer predictions are frozen before Original captures. A separate four-second program uses one second of the low-burst stimulus followed by three seconds of silence, exercising the delayed threshold fall. The [control auditor](../../tools/audio/noise/rmx_noise_sidechain_control_audit.py) regenerates all seven predictions:446,176 modulation values, and906,295 values including detector and threshold, match the complete Original float32 streams exactly. Reversed timelines are rejected. This is control agreement, not identity of the independent random Noise audio.

The [native probe](../../tools/probes/noise_sidechain_probe.cpp) accepts either synthetic stereo blocks (`--chain`) or a threshold plus32 detector values (`--component`) on binary stdin. Build with C++20 and `-ffp-contract=off`; the campaign also uses an AddressSanitizer/UndefinedBehaviorSanitizer build. `uv run --locked python -m tools.audio.noise.rmx_noise_sidechain_controls --help` lists the explicit Original host, plug-in, private template and probe inputs. The corresponding `rmx_noise_sidechain_stream` and `rmx_noise_sidechain_control_audit` modules expose the audio-capture and retained-hash replay steps. Published receipts pin their source/binary hashes and declare every synthetic recipe.

## Comparing generated audio

The [bounded audio runner](../../tools/audio/noise/rmx_noise_sidechain_stream.py) compares three fixed User programs at48k/120BPM, with the same one-second synthetic patterns repeated throughout the input. Each preset first gets a separate eight-second zero-Noise-amount capture. Both transports' residual after subtracting the known input with its32-frame delay is exactly zero after warm-up. This prevents dry input from dominating the Noise comparison.

The original180-second input guard in our capture host blocked a longer synthetic input. A separate host build raises only that guard/message to1204 seconds; the manufacturer's executable is unchanged. Two short programs, including Sidechain with asymmetric input, retain complete audio and five auxiliary hashes across the old and new hosts. Fixture input-length and read-only summary-array errors also stopped before producing fidelity results and cleaned their temporary audio.

The campaign retains three180-second stationary comparisons and extensions of the exact same presets to600 stationary seconds, after four seconds of warm-up. No DSP or margins change between them, and overlapping captures are not pooled. Whole-capture gates remain0.5dB per meaningful band,0.1dB level and0.02 stereo correlation, with a−40dB meaningful-band floor.256-frame Hann windows every128 frames are grouped into four quarter-second stimulus phases. Full, early-third and late-third profiles must all pass, as must each source's early/late stationarity. Paired two-second log powers use the existing short HAC correction and3.0 uncertainty multiplier.

The [independent auditor](../../tools/audio/noise/rmx_noise_motion_power_audit.py) recomputes the retained overall/profile intervals, masks, subwindow verdicts and aggregate qualifications. Overall and profile3dB gain errors must be rejected. Reversing stimulus-phase bins is retained as a diagnostic; it is inconclusive for the weakly modulated low-burst preset and is not represented as a rejected negative. The separate complete-control observations test the actual timing directly.

| New preset |600-second result |
| --- | --- |
| Mild width, main73, Sub2=29, low bursts | Unqualified: overall/profile and stationarity remain inconclusive. Whole-level differences are about+0.072/+0.066dB, with interval upper bounds+0.112/+0.105dB. |
| Default width, main149, Sub2=117, asymmetric stereo | Unqualified: overall, full profile, stationarity and late profile pass; early profile remains inconclusive. One early level interval crosses−0.1dB. |
| Wild width, main203, Sub2=223, steps | Qualified for this declared program: all gates pass. |

All three180-second aggregate qualifications remain false. The600-second extension qualifies one of the three new audio programs. Exact controls and successful delivery do not upgrade the other two verdicts, and these results do not justify retuning a gain or relaxing a margin.

## Delivery, regressions and retention

The signed AU/VST3 bundles reproduce native decoded samples exactly in all16 comparisons: Default and the three new presets, each with low and asymmetric inputs in each format. Each format also passes359 runtime checks.22 preceding static/resonance programs, nine deterministic modulation programs and one Random program preserve complete three-second WAV identity against the preceding engine. Sidechain intentionally changes.

Eight affected native groups, two sanitizer groups and seven Python tooling tests pass, including active Gate/Drive extraction invariance, Sidechain reset/release and a dry-subtraction test that rejects a one-sample alignment error. The engine object is50,368 bytes,128 bytes larger than the preceding checkpoint; prepared audio buffers remain30,100,112 bytes. The exercised callback allocation guards pass. Firmware-host remains15/16, with the inherited `full_integration: Full engine factory path is silent` failure.

Long captures retain one synthetic input WAV and one rendered WAV at a time, under512MiB; the measured peak is below443MiB. Native audio is summarized and deleted before the sanitizer render, then deleted before the Original render. Only compressed powers, hashes, small numerical reports and one current playable preview remain. No new raw test audio or private state payload is retained in the repository.

Random's generated audio, the two inconclusive Sidechain presets, arbitrary music, changing knobs/settings, other rates/tempos, independent source combinations, broader activation gestures and physical hardware still need separate work. The preceding Wild/Saw weak-band result was still inconclusive at this checkpoint and is resolved by the linked production-arithmetic follow-up.
