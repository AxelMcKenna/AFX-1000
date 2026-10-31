# Noise resonance and modulation investigation

1 November 2026. The48k Noise resonance path now uses the calibrated stereo filter and measured feedback control. All nine new width/character presets and the separate failed-case regression pass600-second level/spectrum, stereo and early/late-third checks. The former resonance fallback generated mono noise and used a generic filter. Static width behavior remains unchanged in twelve complete rendered-WAV comparisons against the preceding qualified engine.

The [validation receipt](measurements/2026-11-01-noise-resonance-validation.json) links the declared presets, Original receipts, independent audits, retained powers and delivery checks. Qualification is limited to the reported stationary programs. It does not assign a perceptual accuracy percentage.

## How the control law was reconstructed

The Original was loaded through its public state interface with every required Noise customization field and the corrected Default/Mild/Wild popup mapping. Sub2 parameter requests and float readbacks were checked, along with exact retention of the customization. A processing-time Noise button event enables the effect after4800 frames.

A [read-only observer](experiments/noise_advanced_observer.py) sampled nine steady programs: main147, all three resonance characters, and Sub2 at0,128 and255. Each observed render was compared with an ordinary render. Complete audio, plan, before/after state, parameter log and final inventory hashes agreed in every case. Temporary audio was then deleted. The observer checks the known Original executable hash before reading memory and never writes reference memory.

Let `s = max(0, rawSub2 - 3) / 252`, `p = min(rawMain + 50, 255)` and `t = (p - 3) / 252`. The steady feedback is:

```
Default: 0.7 * s + 0.1 * t^16
Mild:    0.5 * s + 0.1 * t^16
None:              0.1 * t^16
```

Float32 operations, including four successive squarings for the sixteenth power, matter. [Separate arithmetic](experiments/noise_controls_audit.py) exactly reproduces both observed biquads, base feedback and final feedback in all nine records. The small main-dependent term remains present for None.

The project retains its own independent stereo excitation. Resonance changes the feedback terms of the existing third-order recurrence and uses the reconstructed band edges for all three widths. It shares the measured half-beat return and the existing User minimum/maximum level mapping. No Original recording or random generator is embedded.

A fresh main217/Mild-width/None-character prediction exposed a0.23dB overall error, exceeding the unchanged0.1dB limit. The sparse fitted numerator was inaccurate around the filter's upper clamp. Above main101, resonance now uses the independently reconstructed main-level curve, with float32 operations:

```
b = 1 - (rawMain - 101) * 0.00194805197
g = (rawMain - 3) * 0.0055210432 * b^8
```

The excitation scale is anchored to the preceding measured high-end calibration. A second [read-only observer](experiments/noise_gain_observer.py) sampled the computed level targets at main173,201 and229; independent arithmetic reproduces both targets exactly at all three settings. Observed and ordinary audio and auxiliary hashes again agree. Lower main positions retain the fitted gain and have no new general qualification. This resonance checkpoint left the existing non-resonance path byte-identical.

The subsequent [modulation campaign](noise-modulation.md) extends this checkpoint to reconstructed Triangle/Saw/Square cutoff motion. It preserves the static/resonance path and reports its remaining weak-band uncertainty separately.

Review caught a coefficient-cache collision between maximum Default resonance and modulation mode with an unused Mild resonance selection. The cache fields now occupy separate ranges, and a regression check exercises that exact transition. Other checks sweep every main position, width and character at Sub2 endpoints/deadband boundaries for finite, bounded stereo output and verify that None ignores Sub2 while Default changes its response. These are functional checks; setting-change transients have no Original qualification yet.

## Fresh comparison and uncertainty

Three initial180-second stationary programs pass overall level/spectrum equivalence, but their early/late comparisons are inconclusive. Those aggregate qualifications remain false. The first600-second campaign was deliberately stopped after review found the cache collision; its two completed cases remain recorded as partial evidence, separate from the final build.

The next candidate's four completed600-second predictions include that failed main217 case. The campaign was stopped to correct the level law, and its failure stays failed. The final campaign uses nine new holdout settings spanning all width/character combinations, plus a separate recapture of the failed case. It changes main, Sub1, Sub2, minimum/maximum levels and callback sizes. The three main positions also appear in the separate scalar-level verification; no coefficient fitting used these whole-audio comparisons. Each corrected candidate is frozen before its corresponding fresh Original render. Complete optimized/sanitizer WAV identity is required before each statistical comparison. The existing0.5dB band,0.1dB level and0.02 stereo-correlation margins are unchanged; qualification also requires early/late-third equivalence. The independent auditor recomputes every retained interval and rejects a3dB gain error.

All ten final programs pass. AU and VST3 each deliver those ten programs and the Default control with exactly equal decoded stereo samples to the native engine and latency32. Each format also passes359 runtime checks. Seven affected native test groups, two sanitizer groups and five Python tooling tests pass. Firmware-host remains15/16 with the inherited `full_integration` factory-silence failure. These delivery and functional checks have separate scopes from Original fidelity.

## Modulation discovery and remaining scope

Five additional observations cover Triangle, Saw, Square, Random and Sidechain at main147/Sub2=128. In each, the observed cutoff position is reproduced by:

```
effectiveMain = clamp(rawMain + trunc((1 - lfo) * 50), 0, 255)
```

Applying that position to the reconstructed band-edge law exactly reproduces the two observed biquads and feedback values for every selection. All five observed/ordinary renders also have identical audio and auxiliary hashes. This establishes the cutoff destination at those observation points. It does not qualify the waveform generator, phase, clock, input envelope or resulting modulated audio. The current modulation approximation still needs replacement and fresh time-resolved comparisons.

Static resonance evidence is at48k,120BPM, silent input and the declared User presets. Other sample rates/tempos, dynamic knob/settings transitions, sidechain stimuli, wider setting combinations, listening judgments and physical hardware remain open. The inherited firmware-host `full_integration` factory-silence failure is tracked separately.

## Retention

Rendering uses one case at a time, a512MiB temporary-data ceiling and automatic cleanup, including interruption. Only small numeric reports, hashes and compressed block powers are retained. Raw Original listings, native state files and recordings remain private; new raw test audio is not retained. See the [retention policy](artifact-retention.md).

## Reproducing the checks

The native fixture accepts version2 `RMX_NOISE_USER` schedules, adding raw Sub2, mode, wave and character to the existing static fields. `tools/rmx_noise_user.py` generates the matching public Original state and plan. Supply the declared case controls as a JSON list to `python -m tools.rmx_noise_stream --recipe CASES.json --duration 600`, together with the renderer, sanitizer, Original host/bundle, template state and new output report paths. The runner checks receipts/readbacks, hashes predictions before reference capture, saves powers and deletes each case directory. Active modulation is explicitly rejected by this stationary runner.

For scalar observations, render the same plan normally and under LLDB. Set `RMX_NOISE_SCALARS` to a new JSON path, import the appropriate observer and use the same host `render BUNDLE SILENCE PLAN OUTPUT BLOCK` arguments. The control observer ignores1800 Noise calls and reads one record; the gain observer then reads the computed level targets. Compare all six audio/auxiliary hashes before deleting both captures. Run `research/audio/experiments/noise_controls_audit.py --scalars DIRECTORY --output NEW.json`, with `--modulation` or `--gain` for those groups. The retained powers can be audited independently with `python -m tools.rmx_noise_power_audit --report REPORT.json --output NEW.json` after the raw audio is gone.
