# Reverb Up network identification

27 October 2026. Original RMX-1000 Plug-in 2.2.0, factory Default Up, stereo 48 kHz, 120 BPM, Main raw128 and Sub1 raw128. This continues the full sound-matching goal; it does not establish the other controls, production Up, or hardware equivalence. The [reference-method guide](reference-method.md) explains the experiment's general rules.

## Result

The [autonomous static candidate](measurements/2026-10-27-reverb-up-neutral-validation-48k.json) passes **28/28** complete whole/wet/post-input-tail comparisons. Twenty are existing identification/development/component recordings; eight were newly captured after [freezing the candidate](measurements/2026-10-27-reverb-up-neutral-predictions.json). The new set uses two new stereo programs, each at four previously untested cutoff positions: 19, 111, 203 and 247. Audio starts after a one-second silent pre-roll. Duplicated calibration baselines and silence are included in the count and annotated by role.

Fresh worst whole/wet/tail per-channel relative RMS errors are about **0.0013%/0.0026%/0.0039%**. Across all 28 cases, worst wet/tail errors are about **0.0033%/0.0047%**. Every screen retains the 1% limit, reference-channel summed-energy floor `1e-20`, silent-channel absolute RMS limit `1e-8`, reference crop32 and candidate crop0. No comparison gain or wet alignment is fitted. The static dry trace is input at unity; the candidate independently generates the complete reverberation, without a reference wet stem or original reverb output as its input.

The [research C++ renderer](experiments/reverb_up_neutral_probe.cpp) is separate from the live Engine. The Engine's Reverb Up remains the earlier approximation. Main/Sub1 maps, moving controls, cold input, activation, other profiles/rates/tempos, overload, listening and physical hardware remain unfinished.

## What changed from Down

A straightforward reuse of Down's network misses Up's frequency-dependent feedback. The [identification record](measurements/2026-10-27-reverb-up-neutral-model.json) supports five paired cross-coupled combs, followed by the same two all-pass stages per channel, with these neutral-setting delays:

| Pair | Left frames | Right frames |
| --- | ---: | ---: |
| 1 | 509 | 565 |
| 2 | 523 | 915 |
| 3 | 565 | 967 |
| 4 | 945 | 550 |
| 5 | 983 | 587 |

Up adds a **25 Hz first-order high-pass in each comb's feedback path**. The return sums taps before that filter. Input instead passes through a second-order band-pass with fitted poles, rather than Down's fixed 80 Hz high-pass/10 kHz low-pass pair. At this control point, its equivalent center/Q are approximately 437 Hz/0.607. Its numerator is proportional to `1-z^-2`; gain is separately identified. Output retains the measured variable 54..6310 Hz high-pass, fixed 17,330 Hz low-pass, and `1 + 0.5*Sub2Raw/255` level compensation. All-pass delays are left335/1091 and right395/1031, with gain0.7.

This structure was not inferred exclusively from black-box recordings. Inspection of the locally installed original's control/DSP path suggested an Up-only input biquad and feedback high-pass. No original executable, disassembly or instruction listing is distributed. Independent I/O measurements determine the committed numeric calibration and test the resulting model; topology remains an empirical candidate rather than manufacturer attribution. The [manufacturer documentation index](https://www.pioneerdj.com/en/support/documents/rmx-1000/?all=0) is an external entry point for user manuals, not evidence for these hidden coefficients.

## How it was identified

The [tool](../../tools/rmx_reverb_up.py) first verifies the original left/right impulse recordings against exact samples, settings, extent and receipt hashes. A regularized inverse using the earlier Down transfer locates candidate arrival times only; it is deliberately not accepted as Up's input-filter model. A unique pairing of left/right delays must reproduce the cross-channel arrival sums. Removing the diffuser phase makes the two cross-channel transfers agree to about 5.3e-7 relative error, supporting the shared diffuser/symmetric-network hypothesis.

For one pair, write `L=gL*z^-dL`, `R=gR*z^-dR`, and `H` for the feedback high-pass. Left-input direct/cross transfers are:

```text
left  = L / (1 - L*R*H^2)
right = L*R*H / (1 - L*R*H^2)
```

Sum those transfers across the five pairs, then apply the shared input filter, output filters and channel diffuser. The stereo transfer ratio cancels the shared input/output filter. This permits fitting scalar feedback gains from the left-input recording before fitting the input band-pass. Right input informs geometry/diffuser symmetry; it does not supply the feedback/input-filter gain fit.

The rejected unfiltered-feedback hypothesis has about **10.39% stereo frequency-ratio residual**. Including the feedback high-pass lowers that component residual below `1e-4`; the complete fitted frequency response has about **0.0024%** relative error. These are identification screens, not substitute waveform acceptance tests. Full time-domain renders and the later fresh recordings provide the separate acceptance evidence.

## Audit and implementation checks

The [28-capture audit](measurements/2026-10-27-reverb-up-neutral-audit.json) verifies all recipes, receipts, state/log/inventory hashes, every immediate/final readback, comparison output hashes, the frozen source/model/renderer/sample binding and the fresh session's copied prediction. Twenty-seven initial direct-only prefixes, 128 samples each, are bit-identical across original, candidate and input; the silent case stays zero. A one-frame candidate shift fails both whole and wet gates.

Five changed-recipe guards, seven changed-prediction guards and nine invalid/existing-output requests are rejected. The shared WAV loader's separate non-finite policy is checked explicitly: NaN input is replaced with zero and renders silence. Numeric control NaNs are rejected. An initial audit test had incorrectly assumed the loader rejected NaNs; the corrected check follows the existing loader contract without changing the candidate or waveform gates.

Two full candidate renders are byte-identical between optimized and AddressSanitizer/UndefinedBehaviorSanitizer builds. Compile recipes and fresh object hashes confirm that the research DSP and shared WAV IO were instrumented. Eight relevant core CTest groups pass. The [verification summary](measurements/2026-10-27-reverb-up-neutral-checks.json) records these checks and their hashes. Whole-file WAV buffers allocate in this offline fixture; this is not an MCU/callback qualification.

## Reproduce

Use the separately acquired original plug-in, compatible Intel reference host, reviewed 48 kHz bypass calibration, and earlier initial/filter sessions. Original binaries and captures stay under ignored `build/artifacts/research/`; committed records retain hashes and numeric findings.

```sh
uv sync --locked
cmake -S . -B build/reverb-up -DCMAKE_BUILD_TYPE=Release \
  -DRMX_BUILD_PLUGINS=OFF -DRMX_BUILD_REFERENCE_HOST=OFF
cmake --build build/reverb-up --target rmx_reverb_up_probe
uv run --locked python -m tools.rmx_reverb_up --help
uv run --locked python -m tools.rmx_reverb_up_audit --help
```

Run `identify --initial INITIAL_SESSION --calibration CALIBRATION --report NEW_MODEL --header NEW_HEADER`. Compare a regenerated header to the [committed calibration](experiments/ReverbUpNeutralCalibration.h) before deliberately replacing/rebuilding it; reports and headers must be new. `predict --model MODEL --calibration CALIBRATION --renderer RENDERER --report NEW_PREDICTION` freezes the candidate before `capture --prediction NEW_PREDICTION`, with the original host/plug-in and new session directory.

Use `compare --model MODEL --calibration CALIBRATION --renderer RENDERER --session initial INITIAL_SESSION --session filters FILTER_SESSION --session holdout HOLDOUT_SESSION --output NEW_DIRECTORY`. The comparator fixes reference/candidate offsets at 32/0. The audit accepts all three sessions, comparison JSONs, frozen prediction/model/calibration, optimized and sanitizer renderers, its sanitizer build directory and a new output directory. Build the complete sanitizer core/fixture with `-fsanitize=address,undefined` compiler/linker flags, `-fno-omit-frame-pointer`, and exported compile commands. Historical frozen hashes require their recorded source version.

The next required step is measuring Up's Main/Sub1 maps and their interaction, followed by motion/startup validation and live Engine integration. Passing a neutral-setting model does not complete full-device 99% fidelity.

## Dense controls: first identification checkpoint

Two 256-position sweeps now measure Main at Sub1-128 and Sub1 at Main128. All 512 recordings pass their coefficient-structure fitting screen, but the [saved Sub1 forecast](measurements/2026-10-27-reverb-up-control-first-checkpoint.json) fails its unchanged `2e-6` gain-coefficient limit at **155/256 positions**, with worst error about `2.45e-5`. The [first amount report](measurements/2026-10-27-reverb-up-amount-first-identification.json) retains every failed forecast; this is not an accepted full-control waveform model.

The [Main identification](measurements/2026-10-27-reverb-up-main-first-identification.json) supports a fourth-power shrinking-room curve, suggested by eight earlier positions. Its straightforward float32 expression predicts 2,519 of 2,520 active integer taps exactly; Main104's fifth left tap is measured at 1,368 frames rather than the predicted 1,367. The curve assessment is retrospective, since dense capture was already underway. Exact measured delays remain authoritative. Feedback-filter arithmetic/identification precision needs investigation before reusing the neutral gains as a Sub1 scaling anchor. No live Up DSP changes accompany this checkpoint.
