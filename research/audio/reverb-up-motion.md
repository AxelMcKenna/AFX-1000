# Reverb Up control motion and startup

27 October 2026. Original RMX-1000 Plug-in 2.2.0, factory Default Up, stereo 48 kHz, 120 BPM. The autonomous [research processor](experiments/ReverbUpMotion.cpp) passes **101/101 moving-control/startup cases** and **1,204/1,204 prior static regressions**. The later [bounded core checkpoint](#bounded-core-processor-27-october-2026) preserves all 1,305 prior cases and passes eight further fresh recordings. The live Engine's Up processor is still approximate. This is a scoped waveform result; full-device 99% fidelity remains unfinished.

## Current evidence

The [motion comparison](measurements/2026-10-27-reverb-up-motion-validation-48k.json) separates **69 development regressions, 16 earlier prediction-bound cases now used as regressions, and 16 new recordings captured after freezing the corrected candidate**. The [static comparison](measurements/2026-10-27-reverb-up-motion-static-regressions-48k.json) reruns earlier calibration/regression recordings through the stateful processor. These are not 1,305 blind tests. The [checks summary](measurements/2026-10-27-reverb-up-motion-checks.json) binds the reports and records their roles.

| Worst per-channel relative RMS error | All 101 motion cases | Fresh 16 only |
| --- | ---: | ---: |
| Whole output | 0.01253% | 0.01253% |
| Predicted-dry-subtracted wet output | 0.03080% | 0.03080% |
| Post-input tail | 0.007864% | 0.004424% |
| Wet event window | 0.8177% | 0.1554% |
| Wet startup window | 0.08961% | 0.08961% |

Every whole/wet/tail/event/startup screen must pass **1% independently on each channel**. A whole-output average cannot override a failed wet event. Reference summed energy at most `1e-20` switches to absolute RMS limit `1e-8`. Both recordings are cropped by exactly **32 frames**. No comparison gain or wet alignment is fitted. Subtracting the candidate's predicted dry trace from both sides is diagnostic; it is not an independently recorded wet stem.

The fresh set changes random seeds, chirp/tones, pulse locations, initial controls, event times, destination controls and callbacks. It exercises Main's silent edge and high-level transition, combined controls, interrupted moves, early activation, cold input, silence gaps and 18/90-second tails. Callbacks range from 8 to 4,096 frames, including partial internal blocks. This extends the [static identification](reverb-up.md); it does not exhaust all gestures or initial states.

## How the experiment works

Generate exact stereo samples and a timed control recipe. Render them through the separately acquired original Intel plug-in and independent C++ candidate. Check source samples, extent, tempo, factory profile, selected Up button, initial/event/final readbacks, receipts and auxiliary hashes before scoring audio. The candidate receives source samples and declared controls, never original reverb output or a reconstructed original wet stem.

The [first 69 original captures](measurements/2026-10-27-reverb-up-motion-original-characterization.json) comprise twelve button cases, thirty-one step/baseline cases, twelve ramp/baseline cases, six callback repeats and eight cold-input cases. They deliberately reuse earlier Down diagnostic recipes, including its startup-v3 recipes, to isolate Up's differences. Each reference is rendered by Up; recipe reuse does not make those recordings a blind Up holdout. All six 32/256-frame callback repeats are bit-identical to their corresponding 128-frame originals.

Local read-only inspection of the installed original's control/DSP path informed the clocks, gain placement and cache hypotheses. This is not exclusively black-box identification. Debugger-assisted original renders are checked byte-for-byte against normal originals to detect interference. Numeric observations, binary/log/script hashes and independent I/O comparisons are committed. Original executables, instruction listings, raw debugger logs and WAV captures remain outside the published source. Zero-source debugger audio matching silence is an interference check, not waveform-fidelity evidence.

## Discovery and rejected models

| Candidate checkpoint | Passing development cases | Change |
| --- | ---: | --- |
| [First prototype](measurements/2026-10-27-reverb-up-motion-first-prototype-48k.json) | 47/69 | Up network/static maps with an initial Down-derived timing hypothesis |
| [Fast input filter](measurements/2026-10-27-reverb-up-motion-fast-filter-prototype-48k.json) | 53/69 | Separate fast Main filter and asymmetric Sub1 level clocks |
| [Fast send](measurements/2026-10-27-reverb-up-motion-fast-send-prototype-48k.json) | 59/69 | Input send follows fast Main rather than slow room geometry |
| [Fractional geometry](measurements/2026-10-27-reverb-up-motion-fractional-prototype-48k.json) | 63/69 | Measured fractional endpoints and hidden Main0..3 state |
| [Direct-form-I trial](measurements/2026-10-27-reverb-up-motion-direct-form-i-prototype-48k.json) | 63/69 | Rejected as a solution to the remaining failures; reverted |
| [Float feedback](measurements/2026-10-27-reverb-up-motion-float-feedback-prototype-48k.json) | 63/69 | Correct scalar arithmetic; gain placement still wrong |
| [Split gain placement](measurements/2026-10-27-reverb-up-motion-gain-placement-development-48k.json) | 69/69 | Fast post-filter boost separated from slow return attenuation |

### Separate control clocks

The [clock observations](measurements/2026-10-27-reverb-up-motion-clock-observations.json) reveal two Main states. Input-bandpass coefficients advance one raw position per 32-frame block. Room geometry moves one adjacent position on an adaptive clock: its period starts at 60 blocks, approaches `15-min(5,abs(target-current))` one block at a time, and interpolates fractional delays sample by sample. Main motion defers Sub1. Sub1 feedback advances one raw step every five blocks; return-level ramps use 1,500 blocks when increasing and 2,000 when decreasing. A Main-triggered return target ramps for 160 samples.

The [fractional calibration](measurements/2026-10-27-reverb-up-fractional-geometry-calibration.json) measures all 256 settled Main positions. All 2,520 audible integer taps agree with separate I/O identification, but a nominal quartic calculation misses 1,569 of the 2,560 fractional endpoints, by up to about 0.00293 sample. Main0..3's input bandpass is identity, although its stored room state matters when leaving the silent edge. Descending through that edge with nonzero input corroborates the identity transition.

An initial debugger sweep hit its 120-second watchdog after 150 rows. That incomplete artifact is retained and excluded from calibration. A complete run using the supported 600-second watchdog supplies calibration; a separate hardware-watchpoint observation [corroborates all 2,560 targets](measurements/2026-10-27-reverb-up-fractional-geometry-corroboration.json). The generated [calibration header](experiments/ReverbUpMotionCalibration.h) contains numeric measurements.

### Arithmetic and gain placement

The [scalar replay](measurements/2026-10-27-reverb-up-motion-scalar-replay.json) uses separately measured endpoints and the observed clock to reproduce the checked delay, feedback coefficient and counters exactly across **4,200/4,200 blocks** of Main128→192. Feedback target, increment and each addition round to float32; delay increments are samplewise. Nominal fractional endpoints, double feedback updates and once-per-block delay updates each fail this component check. Selected scalar equality does not establish full audio agreement: six waveform failures remained recorded.

The [gain factorization](measurements/2026-10-27-reverb-up-motion-gain-factorization.json) explains those six. A static wet gain had conflated stages with different clocks. Input has constant float32 `0.189` scaling before the bandpass and a fast-Main boost `1 + 0.8*u^4` afterward, where `u=max(0,Main-3)/252` with explicit float32 multiplication order. Independent static I/O and observed levels agree at all 252 audible Main positions, worst discrepancy about `5.83e-8`. Return level follows slow geometry and Sub1; attenuation above Main197 belongs there. Applying all static attenuation to the fast input send gives wrong transients. Correct placement resolves all 69 discovery cases.

The network retains five cross-coupled comb pairs with measured feedback high-pass coefficients, two all-passes per channel, the measured input bandpass and Sub2 output high-pass/fixed low-pass. Up's dry gain stays unity. Two float32 input-fade multiplications, a 160-sample button gate, 388 muted warm-up blocks (12,416 samples) and the observed initially empty first right-comb path govern startup. Geometry/feedback increments pause during warm-up while target/counter handling continues. This persistent state is independent of the offline WAV fixture.

## The failed first holdout and the 40-sample discovery

After 69/69, freeze the [first prediction](measurements/2026-10-27-reverb-up-motion-first-predictions.json), then capture sixteen different source/control programs. **Only 15/16 fresh cases pass**, giving [84/85 overall](measurements/2026-10-27-reverb-up-motion-first-holdout-48k.json). Case `up-motion-holdout-3` moves Main0→224 at frame192031 with Sub1-253. Whole/wet/tail errors are below 1%, but its wet event window fails at **35.306%**. Git checkpoint `5192d4c` preserves the failed candidate and report.

All ten delay-geometry vectors agree through the failing transition; adding a Main0 gate fade is unsupported. Inspecting the original's delay transfers instead reveals reads of **40 float samples** into **64-sample cache slots**. Eight independently observed queued reads cover all four slots twice. Across 350 observed blocks, all 96 padding values checked per block are zero. A transfer count of 64 seen elsewhere belongs to a write, not the measured read window.

When geometry shrinks quickly, a sample requested later in the current 32-frame block can lie beyond the 40 fetched samples. An ideal circular-buffer lookup returns history there; the observed cache returns zero. The candidate reproduces that boundary without allocating a cache: save each delay's integer length at block start, then compute

```text
index = 1 + sample_in_block + floor_delay_at_block_start - floor_delay_now
tap = actual_history_sample if 0 <= index < 40 else 0
```

The zero also participates in feedback. The [causal corroboration](measurements/2026-10-27-reverb-up-read-window-corroboration.json) combines separately measured geometry with the declared callback/event schedule. It predicts first out-of-window internal frame **193182**, emitted at physical frame **193213**, or **193181 after fixed crop32**. Old/corrected candidate WAVs first differ at exactly **193181**. These axes account for partial-callback FIFO timing; output was not shifted to find a match. An earlier mapping helper omitted that partial callback and was corrected before accepting the proof.

This reduces the failing case's maximum wet-event error to **0.006566%** and [all 85 existing cases pass](measurements/2026-10-27-reverb-up-motion-read-window-development-48k.json). Since the failure informed the fix, those sixteen cases become regressions. The original failure remains a negative control. All 1,204 static output and dry-trace WAV hashes are unchanged before/after the read-window correction.

Only then freeze the [second prediction](measurements/2026-10-27-reverb-up-motion-second-predictions.json), change sources, controls, event times and callbacks, and capture sixteen further originals. **16/16 fresh cases pass**, giving the current 101/101 result. This supplies prospective evidence for the corrected processor; it does not erase the failed first forecast.

## Audit and practical limits

The [final audit](measurements/2026-10-27-reverb-up-motion-audit.json) independently recomputes all 1,305 whole/wet/tail comparisons and every motion event/startup window. It verifies recipes, original host/bundle identities, receipt/auxiliary hashes, immediate/final readbacks, candidate/schedule/dry hashes, frozen source/model/calibration/renderer/sample bindings, and each session's copied prediction. Historical predictions stay attached to their earlier candidate; current comparisons label those cases as regressions.

It checks 1,203 bit-identical static direct-only prefixes and forty numerically identical non-silent cold prefixes across original/candidate/predicted dry. Cold bit-exact flags are recorded separately because signed zero can differ. It rejects seven altered recipes, eight altered predictions and twenty malformed/existing-output native requests. Non-finite WAV input follows the existing NaN-to-zero loader policy. Settled bypass is bit-exact at nominal32 and fails offsets0/31/33. A source/control change at frame15013 leaves earlier output/dry bit-exact with identical callback split points, while later output changes.

Two complete fresh programs produce byte-identical optimized and AddressSanitizer/UndefinedBehaviorSanitizer output/dry WAVs. Compile recipes and object freshness cover research DSP, fixture and shared WAV IO. Eight core CTest groups pass. [Checks and hashes](measurements/2026-10-27-reverb-up-motion-checks.json) record the evidence.

The research class allocates history/callback storage in `prepare`; the offline fixture allocates full WAV buffers. At this research checkpoint, allocation interception and resource qualification had not yet been established; the later bounded-core section provides that separate native evidence. MCU deadlines, a fresh firmware cross-build and live Up integration remain unfinished. Integer controls at factory Up, stereo48k/120BPM are the measured scope. Fractional controls, other profiles/rates/tempos, wider gestures, effect combinations, overload, listening and hardware still require work. Spiral and remaining device features also prevent a full-device 99% claim.

## Reproduction

Use the separately acquired original plug-in, compatible Intel host, reviewed bypass calibration and static model. Binaries/WAVs stay under ignored `build/artifacts/research/`; committed reports retain hashes. All output/session/report destinations must be new. Historical frozen reports require their recorded source/renderer versions. A different build path/toolchain can change binary hashes and requires a new prediction before new capture.

```sh
uv sync --locked
cmake -S . -B build/reverb-up-motion -DCMAKE_BUILD_TYPE=Release \
  -DRMX_BUILD_PLUGINS=OFF -DRMX_BUILD_REFERENCE_HOST=OFF
cmake --build build/reverb-up-motion --target rmx_reverb_up_motion_probe

UP_MODEL=research/audio/measurements/2026-10-27-reverb-up-static-control-model.json
UP_RENDERER=build/reverb-up-motion/rmx_reverb_up_motion_probe
# Set UP_CALIBRATION to the reviewed bypass calibration, UP_HOST to the
# compatible original host, and UP_PLUGIN to the separately acquired bundle.
uv run --locked python -m tools.rmx_reverb_up_motion predict \
  --stage holdout-v2 --model "$UP_MODEL" --calibration "$UP_CALIBRATION" \
  --renderer "$UP_RENDERER" --report build/new-up-prediction.json
uv run --locked python -m tools.rmx_reverb_up_motion capture \
  --stage holdout-v2 --model "$UP_MODEL" --calibration "$UP_CALIBRATION" \
  --prediction build/new-up-prediction.json --host "$UP_HOST" \
  --plugin "$UP_PLUGIN" --session build/new-up-holdout-v2
uv run --locked python -m tools.rmx_reverb_up_motion compare \
  --model "$UP_MODEL" --calibration "$UP_CALIBRATION" \
  --renderer "$UP_RENDERER" --session holdout-v2 build/new-up-holdout-v2 \
  --output build/new-up-comparison
```

Re-recording published recipes reproduces them; it is not a third unseen holdout. For the complete comparison, supply seven `--session STAGE DIRECTORY` pairs: `button`, `steps`, `ramps`, `blocks`, `cold`, `holdout`, `holdout-v2`, plus `--historical-prediction holdout FIRST_PREDICTION`. The first five can be captured separately as discovery without predictions. `characterize --session STAGE DIRECTORY` checks original recipes/readbacks and callback/baseline differences.

Run `uv run --locked python -m tools.rmx_reverb_up_motion_static` with the same model/calibration/renderer, a new output directory and eleven `--session STAGE DIRECTORY` pairs: `main`, `amount`, `main-long`, `amount-large`, `initial`, `filters`, `timing`, `long-tail`, `neutral-holdout`, `mixed`, `mixed-v2`. This rerenders prior static originals through the motion candidate.

Build a separate complete sanitizer core/fixture with compiler/linker `-fsanitize=address,undefined`, `-fno-omit-frame-pointer` and exported compile commands. `uv run --locked python -m tools.rmx_reverb_up_motion_audit --help` lists explicit audit inputs: model/calibration/current prediction, both comparisons, optimized/sanitized renderers and sanitizer build, read-window proof, retained negative comparison, seven motion/eleven static sessions, historical first prediction and a new output directory. The published audit also requires the preserved failed first candidate WAV in its original comparison directory.

[`rmx_reverb_up_geometry.py`](../../tools/rmx_reverb_up_geometry.py), [`rmx_reverb_up_motion_replay.py`](../../tools/rmx_reverb_up_motion_replay.py) and [`rmx_reverb_up_read_window.py`](../../tools/rmx_reverb_up_read_window.py) provide `--help` for endpoint calibration, scalar replay and causal read-window checks. Their raw local debugger inputs are hashed in the numeric reports but not distributed.

Next qualify runtime/resources and integrate Up into the live Engine while retaining these reference gates. Integration and broader device work remain separate deliverables.

## Bounded core processor: 27 October 2026

The measured algorithm is now available as [`CalibratedReverbUp`](../../include/rmx/CalibratedReverbUp.h), implemented in [`src/core/ReverbUp.cpp`](../../src/core/ReverbUp.cpp). The live Engine does not select it yet. The earlier research files remain a reproducible historical snapshot. Both promoted calibration headers are byte-identical to their measured research counterparts. The new API additionally rejects partially overlapping output/dry spans before consuming state; valid callback DSP is preserved.

All [1,305 previous output and dry WAVs](measurements/2026-10-27-reverb-up-production-regressions-48k.json) are byte-identical to the audited research processor. Exact identity of both traces carries the preceding whole/wet/tail/event/startup acceptance results; the regression report does not present inherited scores as new independent measurements. Original recipes, samples, receipts, auxiliary hashes and immediate/final readbacks are rechecked before rendering each case. Prior audit/report hashes bind the transferred results.

A [new frozen production prediction](measurements/2026-10-27-reverb-up-production-predictions.json) then precedes [eight fresh original captures](measurements/2026-10-27-reverb-up-production-fresh-48k.json). These use different stereo noise/chirps, pulse positions, cold toggles, early simultaneous controls, silent-edge departures, Main197-region motion, interruptions, silence gaps, long decay and callback sizes 8/15/33/63/511/1024/2048/4096. **All eight pass**, giving **1,313/1,313 scoped waveform cases**: 109 motion/startup cases and 1,204 static regressions. Fresh worst whole/wet/tail/wet-event/wet-startup RMS errors are approximately **0.01173%/0.02903%/0.001678%/0.1264%/0.05224%** under unchanged gates and crops32/32.

The [production audit](measurements/2026-10-27-reverb-up-production-audit.json) checks every transferred output/dry/schedule hash, recomputes the eight fresh waveform/window screens, verifies reference provenance/readbacks and original bundle identity, and records eight matching non-silent cold prefixes. Numerical and bit-exact equality are labeled separately. Seven changed recipes, eight changed predictions and twenty malformed/existing-output requests are rejected. Two complete programs and their dry traces are byte-identical in optimized and AddressSanitizer/UndefinedBehaviorSanitizer builds, with DSP, fixture and shared WAV IO instrumented. Eighteen relevant native CTest groups pass; the [checks summary](measurements/2026-10-27-reverb-up-production-checks.json) binds these reports.

The [resource test](../../tests/reverb_up_tests.cpp) measures a **4,056-byte object and 436,384 bytes of prepared buffers** at the 4,096-frame capacity on native ARM64 macOS. Two processors occupy 872,768 bytes in a fixed 1 MiB arena. Each processes 258,902 frames across 512 mixed callbacks, including in-place/separate parity, first processing, controls and resets, with **zero tracked C++ `new` or PMR requests after preparation**. Invalid extents, non-finite samples, overlapping dry buffers and invalid preparation capacities are checked for rejection without affecting later valid processing. Destruction returns arena use to zero. The optimized and sanitized resource programs both pass; [resource measurements](measurements/2026-10-27-reverb-up-production-resources.json) state the instrumentation's limits. This is native resource evidence, not an MCU timing result.

Build `rmx_reverb_up_production_probe` and `rmx_reverb_up_tests`. [`rmx_reverb_up_production.py`](../../tools/rmx_reverb_up_production.py) provides `predict`, `capture`, `compare` and `regress`; each accepts the model, reviewed calibration and production renderer. Freeze before capture, then compare the fresh session. For regression, pass the prior audited motion/static comparison JSONs, their audit, all seven motion sessions and eleven static sessions, and a new output directory. [`rmx_reverb_up_production_audit.py`](../../tools/rmx_reverb_up_production_audit.py) provides `--help` for the fresh/prior evidence, prediction/session, optimized/sanitized renderers and sanitizer build required by its independent checks. Outputs must be new. The CLI's already published programs are reproducible regressions on a later rerun, not unseen future holdouts.

Next integrate the qualified core class into the live Up Engine and check its routing, latency, wrappers and fresh reference programs. MCU deadlines, a fresh firmware cross-build and the broader device-wide sound-matching requirements remain unfinished.
