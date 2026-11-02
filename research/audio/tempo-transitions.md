# Tempo transitions against the Original plugin

The 2 November 2026 checkpoint passes **9/9 tempo regression programs and 9/9 fresh timing holdouts**, with all 18 matched drum/source controls passing. The declared sequence is host-synchronized 120 → 137 → 91 BPM, at 48 kHz with Default settings. Multiple drums, roll/overdub commands, callback sizes, pitch and level exercise the complete shared engine. The holdouts change event timings while retaining that tempo sequence.

These are scoped software comparisons against RMX-1000 Plug-in 2.2.0. They do not qualify every tempo, transport gesture, activation sequence, User profile, musical source or physical RMX-1000. Together with the earlier checkpoint, **50/54 declared active interaction programs** pass. Echo/HPF/Crush control-motion programs and Back Spin combined with Reverb Up remain failed. A coverage count is not device accuracy.

The [regression report](measurements/2026-11-02-tempo-regression.json.gz), [timing holdouts](measurements/2026-11-02-tempo-holdout.json.gz) and [validation receipt](measurements/2026-11-02-tempo-validation.json) retain exact source/binary bindings, plans, hashes and verdicts. The unchanged gates require at most 1% relative RMS error per channel in the complete output, each second, each event window and the active-minus-matched-control signal. Reference-silent channels use a 1e-8 absolute RMS limit. No per-case gain, alignment or crop is fitted.

## What changed

**Delay retiming.** The reference truncates the beat duration to whole milliseconds. Its quarter/half/three-quarter/one-beat return taps therefore use 6000/12000/18000/24000 frames at 120 BPM, 5244/10488/15732/20976 at 137, and 7908/15816/23724/31632 at 91. A tempo change does not immediately move the read position. Each tap fades out for 160 samples, changes its stored delay length at zero, then fades in for 160 samples. The read cache retains the old length through the complete final 32-frame block. The faded return also feeds the feedback loop.

The shared [retiming component](../../include/rmx/DelayRetiming.h) now carries that state for the measured Echo/filter and Spiral paths. Echo tracks beat duration separately from its time-knob division. An intermediate model applied the same retiming to time-knob changes and worsened an existing motion failure; that coupling was rejected. Its complete failed Scene campaign remains in provenance. The final model preserves the earlier motion outputs.

**Spiral clocks.** The former measured implementation was restricted to manual 120 BPM. Its pitch and processing clocks now run in the declared synchronized programs. Spiral Up's Default primary delay remains tied to Main, while Spiral Down's Main-to-delay map depends on the truncated beat duration. Down's delay-slew normalization also follows that duration. Both directions use a tempo-dependent envelope averaging count: `max(120, floor(beatMilliseconds × .375))`, giving 187, 163 and 247 updates for the declared sequence.

A zero-input native replay independently reproduces Spiral Down's target, float64 delay trajectory and float32 output-regulator state at all 196 sampled reference blocks. The shared return's delay/gain replay also matches all 196 sampled Spiral Up blocks. These control checks help identify the mechanism; waveform qualification comes from the separately scored full renders.

**Storage.** Four Spiral return rings borrow 72,004 stereo frames each from existing Scene storage, enough for a one-beat return at the engine's 40 BPM lower bound. The complete borrowed Spiral region grows from 132,880 to 324,880 frames. Prepared audio-buffer allocation stays at 30,100,112 bytes. The separate primary/raw rings retain their capacity; measured-path eligibility checks their beat-length bound and falls back outside it. Larger return storage does not establish a sound match across that entire range.

The storage test fills borrowed buffers with NaNs, compares them with zero-filled buffers across complete slow-tempo ring wraps, checks finite fallback transitions at 40/88/91/120/137/240 BPM and enforces zero callback allocations. Native and sanitizer tests run the same case.

## How the reference was checked

The hash-pinned [read-only observer](experiments/scene_selector_observer.py) reads scalar timing, gain and envelope states, never sample buffers. The [driver](../../tools/rmx_performance_path_observe.py) requires ordinary and observed audio, plan, initial/final state, parameter log, final inventory and explicit transport log to be byte-identical. Repeated ordinary renders also match the original audio hashes from the earlier published tempo campaign.

Use `--mode performance-selector --family tempo --effect-index 0`, `2` or `7` with the pinned Intel host, Original bundle, a new output and `--expected-output-sha256` to repeat the retained BPF, Spiral Up and Spiral Down observations. The provenance archive retains the earlier observer revision needed for its first trace.

The first delay-return correction passed five previously failing programs. A Spiral model that changed return timing alone still failed both directions after the first tempo event. Adding the envelope averaging and Down's primary target qualified Up; matching Down's tempo-dependent slew limit resolved the remaining trajectory and waveform error. Failed models and their source snapshots remain in the [provenance archive](measurements/2026-11-02-tempo-provenance.json.gz). No Original assembly or recorded audio is distributed.

## Reproduction and retention

Run `uv run --locked python -m tools.rmx_performance_path --stage fresh --family tempo` with explicit `--renderer`, `--sanitizer`, `--host`, `--plugin` and a new `--output`. Use `--stage fresh2` for the timing holdouts. Optimized and ASAN/UBSAN whole WAVs must agree before each Original render. Independent numerical scoring and negative controls run before audio deletion. The retained-energy auditor can recompute window verdicts afterward.

The final Echo cleanup is bridged by complete optimized/sanitized prediction hashes for both accepted tempo cohorts. Separate preservation compares older manual drum programs, the complete preceding performance cohort and input-only Spiral direction/control programs. Signed AU/VST3 delivery uses its own declared one-shot/MIDI recipe and compares complete samples with the native engine; it does not substitute for Original qualification.

Captures run serially, stay within a 512 MiB temporary-file budget and delete audio automatically. Compact reports, failed hypotheses, source snapshots and one current signed playable build are retained. The audio pause marker and canonical reference installation remain untouched. Exact validation, preservation, delivery, memory and cleanup results are recorded in the receipt.
