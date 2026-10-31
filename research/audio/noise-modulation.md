# Noise modulation clock and moving filter

1 November 2026. Triangle, Saw and Square Noise now move the filter cutoff using reconstructed control trajectories. The preceding approximation modulated output amplitude at musical divisions. This checkpoint covers the declared fixed-control programs at48kHz,120BPM and silent input; it does not assign a whole-device or perceptual accuracy percentage.

The [validation receipt](measurements/2026-11-01-noise-modulation-validation.json) links the control observations, prospective predictions, power summaries, independent audits and delivery checks. [Static Noise resonance](noise-resonance.md) is separate evidence.

Eight of the nine new presets pass every gate after the declared extensions. Wild/Saw at main173 and Sub2=223 remains unqualified: its late-window0–500Hz band in the highest control-value bin is inconclusive. All nine pass their overall and full motion-profile comparisons. The retained data keeps these distinctions explicit.

## Reconstructing the controls

A [read-only observer](experiments/noise_motion_observer.py) samples the32 modulation values produced by each Original Noise call. It hashes the entire float32 control stream and retains a small set of scalar records. Ordinary and observed renders must have identical audio, plan, before/after state, parameter log and final inventory hashes before their temporary directories are deleted. It never reads or copies the manufacturer's random-generator state.

The initial comparison uses three Sub2 positions for each deterministic wave. A second set freezes nine new control-stream predictions before Original observations, and endpoint checks cover visible Sub2 at4 and255. The [control auditor](../../tools/rmx_noise_motion_control_audit.py) replays the complete streams through optimized and sanitizer builds and checks both their hashes and the retained scalar records. These are control values, not generated audio samples.

For steady controls, let `s = max(0, rawSub2 - 3)`. At48kHz the period parameter in samples is `T = 9600 + ((960 - 9600) / 252) * s`, evaluated with the observed float32 operation order. Depth is `min(1, 0.025 * s)`, reaching full depth at visible43. Initial smoothing advances toward `s` by one raw count per sample and clamps the smoothed control to0..252; the final depth of each32-sample block scales its waveform.

| Wave | Measured trajectory |
| --- | --- |
| Triangle | Step by4/T and reflect at−1 and+1. |
| Saw | Rise by1/64 per sample, then descend by2/T, with reflected endpoints. A full rise takes128 samples. |
| Square | Ramp by±1/64, clip at±1, and switch direction using the integer period counter. Its cycle is `floor(T)+1` samples. |

All start from zero before the first increment. The observed filter position is `clamp(rawMain + trunc((1 - lfo) * 50), 0, 255)`. The Original generates controls in32-sample blocks and updates filter coefficients at their first and seventeenth samples. The project follows that16-sample cadence.

One activation comparison identifies first nonzero Original output at frame4864 after a frame4800 button event. The previous native path started at4832. The reconstructed motion path includes the additional activation block and now starts at4864; the shared wrapper latency remains32. This is an onset check for that declared program, not a qualification of every activation envelope or arbitrary event timing.

## Keeping the moving filter's history

The existing third-order recurrence is retained for static Noise and resonance. Moving coefficients need the combined filter input history, including the feedback that was present two samples earlier. Applying the current feedback value to that old sample would give the wrong time-varying system.

The motion path therefore retains `u[n] = excitation[n] + feedback[n] * y[n-1]` and applies the reconstructed biquad to `u[n]` and `u[n-2]`. It uses the same measured width trajectories, high-main gain curve, User level law and half-beat echo. Excitation remains the project's own independent stereo generator. The measured static/resonance renders retain complete WAV identity through the change.

## Audio comparison and uncertainty

Three initial180-second programs remain inconclusive under the combined qualification. All nine new600-second programs pass overall spectrum/level/stereo, early/late stationarity and the full motion-profile comparison. Four retain inconclusive early/late profile subwindows, so their600-second aggregate qualifications stay false. Those exact programs are extended without changing DSP or margins; overlapping captures are not pooled as independent evidence.

The reference host limits additional tail duration. The extension uses1196 stationary seconds after four seconds of warm-up, keeping the same host binary. Fixture and profile-helper duration bounds were extended separately; a source/byte bridge records that these changes alter only offline limits. The first extension attempts stopped at duration guards and cleaned up their audio before producing any reference-fidelity result.

Whole-capture tests retain0.5dB band and0.1dB level margins,0.02 stereo-correlation tolerance and the−40dB meaningful-band floor. The added motion screen uses256-frame Hann windows every128 frames, six frequency bands, and bins conditioned on the independently verified control value. Triangle/Saw use four value bins; Square uses negative plateau, edge and positive plateau bins. Two-second paired log-power differences use the existing short HAC correction and3.0 uncertainty multiplier, with the same0.5/0.1dB margins. Full, first-third and last-third motion comparisons must all pass.

The [independent power auditor](../../tools/rmx_noise_motion_power_audit.py) recomputes every interval, meaningful-band mask, subwindow verdict, stereo gate and aggregate result using separate float64 sums/logs/einsum arithmetic. A3dB gain error and reversed control-conditioned power bins must be rejected. Inconclusive results are retained rather than relabeled.

## Retention and remaining work

The complete control audit covers24 streams and2,188,032 float32 values, including15 prospective predictions. The weak Wild/Saw case received additional read-only diagnostics. Its observed biquad coefficients at effective positions173/174 match the reconstruction exactly. A recurrence replay driven by temporary Original excitation/coefficient records agrees with the observed pre-return output within3.7e-7 relative RMS. A separate timing fit confirms the12,000-frame return,0.35 first tap and0.5 recirculation. The short excitation-spectrum diagnostic is broadly consistent with white noise; it does not explain the remaining band difference.

In that case's last398 seconds, the candidate's mean paired log-power difference in the affected band is+0.584dB left and+0.565dB right. Approximate intervals are[0.431,0.737] and[0.418,0.712]dB, straddling the0.5dB limit. The band contains about0.021% of the corresponding control bin's reference power and remains above the declared meaningful-band floor. It therefore remains inconclusive; the diagnostics do not close the discrepancy.

Both signed plug-in formats reproduce native decoded samples exactly across all20 delivery comparisons: the nine declared presets and Default in each format. Delivery success is independent of Original-fidelity qualification. Each format also passes359 runtime checks. Seven affected native groups, two sanitizer groups and six Python tooling tests pass. The engine object is50,240 bytes,192 bytes larger, with the existing audio buffers unchanged and no new callback allocations in the exercised checks. Firmware-host remains15/16 with the inherited factory-silence failure.

The [bounded runner](../../tools/rmx_noise_motion_stream.py) hashes and summarizes native audio, deletes it, renders/summarizes the sanitizer and Original in turn, and removes the case directory. Only one whole WAV is kept at a time, under512MiB. Small receipts, compressed powers, control hashes and source/binary hashes remain. No new raw test audio is retained.

At this checkpoint Random and Sidechain retained their previous unqualified audio paths. The subsequent [Sidechain follow-up](noise-sidechain.md) reconstructs its detector and envelope, qualifying one declared audio program while retaining two inconclusive programs. Random, changing knobs/settings while sounding, other sample rates/tempos, music-input interactions, listening judgments, broader activation envelopes and physical hardware still need separate reference work. The inherited firmware-host factory-silence failure remains tracked separately.
