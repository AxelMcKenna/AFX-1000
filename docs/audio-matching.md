# Measuring the RMX sound match

The [sound-matching research](../research/audio/rmx1000-fidelity.md) defines the overall target. Static factory Isolator, Echo, BPF Echo, HPF Echo, LPF Echo and Crush Echo pass the declared waveform criterion at 48 kHz. Default Noise also passes its statistical screen at four positions excluded from coefficient fitting. This does not certify a complete device sound match.

## Current reference status

On 26 October 2026, the official RMX-1000 Mac plug-in 2.2.0 was obtained from [AlphaTheta support](https://support.alphatheta.com/en-US/articles/4405128214809?product=4416587889433). Its installer signature, notarization and AU bundle signature verified through macOS trust services. The archive and hashes are retained locally under `build/artifacts/research/reference-acquisition/`; vendor binaries remain outside Git.

The Intel AU uses legacy `thng` registration and was unavailable to `auval` on macOS 26.6.2. The package's signed Intel VST2 now loads successfully through the original minimal public-ABI adapter in `tools/legacy_vst2_host.h`. An x86_64 host runs under Rosetta and opens the extracted bundle directly, without installer scripts. Its identity is `RMX-1000 Plug-in` / `Pioneer Corporation` / `2.2.0`, with 52 public parameters. The project plug-in is used separately as a host fixture and candidate.

At 48 kHz, the original bypass is bit-exact with the input after a 32-sample delay, despite reporting zero latency. Both channels agree. Repeated Isolator/Echo captures at host blocks of 32, 128 and 256 samples were bit-exact for the checked static cases. At 44.1 and 96 kHz, bypass includes extra filtering and different latency; these paths need a separate conversion model and are excluded from the current match claim.

Thirty-five fresh Isolator cases and twenty-five fresh Echo cases at 120 BPM passed the 1% per-channel unscaled RMS-error criterion. Worst errors were approximately 0.0014% and 0.017%, respectively, on independent stereo broadband, chirp, transient and multitone material. Another twenty-five Echo cases pass at 137 BPM. Echo's isolated additive return also passed, with worst error about 0.021%, so the dry signal does not hide its return error. The checked native VST3 cases agree with the core within 1.2e-7 full scale. A clean source snapshot passes all thirty-one CTest groups, with eight offline-host regressions for each project VST3/AU. These are waveform errors within a stated suite, not percentages of perceived similarity. Raw vendor captures remain in ignored `build/artifacts/research/`; the [measurement summary](../research/audio/measurements/2026-10-26-factory-48k.json) preserves hashes and per-case results.

## Reproduce the factory checks

Use the host architecture matching your separately obtained original plug-in. Each output directory must be new. From the repository root:

```sh
uv run --locked python -m tools.rmx_factory_match capture --effect isolator \
  --host /path/to/Intel/RMXReferenceHost --plugin /path/to/RMX-1000Plug-in.vst \
  --output build/artifacts/research/isolator-reference
uv run --locked python -m tools.rmx_factory_match render \
  --session build/artifacts/research/isolator-reference --renderer build/rmx_render \
  --output build/artifacts/research/isolator-candidate
```

Inspect `calibration-unreviewed.json` in the candidate directory. Check the effects-disabled reference plan, candidate preset, channel order, gain, polarity and bypass waveform. Save a reviewed copy with `verified: true`; retain its bypass hashes. Then run:

```sh
uv run --locked python -m tools.rmx_factory_match compare \
  --session build/artifacts/research/isolator-reference \
  --candidate build/artifacts/research/isolator-candidate \
  --calibration build/artifacts/research/isolator-candidate/calibration-reviewed.json \
  --report build/artifacts/research/isolator-candidate/comparison.json
```

For Echo, use `--effect echo` and fresh reference/candidate destinations. The recipe records at least a twelve-second tail, extends it at slow tempos, and supplies the actual reference duration to `rmx_render`. Add `--bpm 137` to capture another fixed tempo. It selects original Auto host synchronization for non-default tempos; simply supplying another host BPM while Auto is off leaves the original at manual tempo. Reference receipts and candidate hashes are checked before comparison. Static checks exclude User-profile maps, control gestures, changing tempo, combinations, overload, analog hardware and rates other than 48 kHz.

Synchronized Echo and Noise use `floor(60000/BPM)` whole milliseconds per beat, before applying the selected division. Clean impulses at 90, 128, 137, 128.5 and 123.9 BPM verify the Echo rule; Noise tails verify it at 90, 128 and 137. See the [clock measurements](../research/audio/measurements/2026-10-26-clock-48k.json). Initial controls now match the original inventory: Auto on, Scene Main/Sub2 at zero, Sub1 at raw 128, and Echo selected for Release.

## BPF, HPF and LPF Echo

The [filter measurement record](../research/audio/measurements/2026-10-26-filter-validation-48k.json) contains 164 passing static comparisons, including fresh stereo broadband/chirp/transient/multitone signals at 120 and 137 BPM, direct impulses and separately assessed tails. The largest per-channel RMS errors across the checked segments are approximately 0.0018% for BPF, 0.0063% for HPF and 0.16% for LPF. Nine additional native VST3 cases pass, including button-off tails. These results apply to factory Normal width, Sub2 zero, default delay assignments and feedback character, at 48 kHz. Other profiles/rates and moving controls retain separate validation requirements.

BPF adds its resonant band-pass output directly to dry input; its echo feed uses 0.85 times that band output. HPF and LPF replace the direct signal through resonant filters. Their common return is high-passed through two Butterworth sections at approximately 284 Hz. Four independent combs have 0.75 feedback and a 0.7 return gain. Sub1 crossfades between quarter, half, three-quarter and one-beat returns: `x=clamp((raw-3)/62.25,0,4)` selects adjacent weights, beginning with a fade from zero to the quarter-beat tap. Main gates the echo send with `clamp((raw-4)/5,0,1)`. Echo tails survive button-off. This differs from the standalone Echo's discrete time regions.

The [numerical identification record](../research/audio/measurements/2026-10-26-filter-identification.json) fits every BPF raw position and a calibrated HPF/LPF feedback map. The latter uses a Butterworth biquad with one-sample-delayed band-pass feedback, itself high- or low-pass filtered through a first-order section. Model identification uses recurrence residuals and reconstructed response error; fresh-signal validation checks the final engine independently.

To reproduce with a separately obtained original and an independently reviewed 48 kHz bypass calibration:

```sh
uv run --locked python -m tools.rmx_filter_capture \
  --host /path/to/Intel/RMXReferenceHost --plugin /path/to/RMX-1000Plug-in.vst \
  --output build/artifacts/research/filter-reference
uv run --locked python -m tools.rmx_filter_identify \
  --base build/artifacts/research/filter-reference \
  --grid build/artifacts/research/filter-reference \
  --calibration build/artifacts/research/filter-reference \
  --report build/artifacts/research/filter-identification.json \
  --header build/artifacts/research/FilterEchoCalibration.h
uv run --locked python -m tools.rmx_filter_match \
  --session build/artifacts/research/filter-reference --renderer build/rmx_render \
  --calibration calibration-reviewed.json --output build/artifacts/research/filter-candidate
```

The capture takes several minutes and writes substantial local audio. Destinations must be new. The identifier verifies reference/input/plan hashes and exact impulse recipes. The matcher verifies capture hashes, applies only the reviewed bypass offset, and assesses each channel without gain fitting. Add `--include-grid` to screen the complete BPF identification grid too. Event plans are reported as skipped by the static CLI matcher and require the native timestamped host; they are not counted as static passes. Raw reference recordings and vendor binaries remain outside Git.

## Crush Echo

The [Crush identification](../research/audio/measurements/2026-10-26-crush-identification.json) separates sample holding from resonant high-pass filtering. The measured held values require no amplitude-resolution reduction. Main uses dry gain `clamp((129-raw)/126,0,1)^2` and the complementary filtered-hold gain. The filter reuses the HPF Echo resonance topology/map, with cutoff rounded to integer Hz from `60*exp(max(raw-4,0)*0.0168583737)`.

The hold period needs the original arithmetic: multiply the raw byte by the rounded float reciprocal of 255, then multiply that float by 24 and round to float again. Keep a double counter, subtract one each frame, and sample both channels when it becomes negative before adding the period. The settled clock begins at input frame 32. Division by 255, an integer interval or a double period product picks different input frames at recurring boundaries. Five seconds of direct-only noise at raw 113, 177, 213 and 253 verifies the clock against observed hold events. Late impulses provide separate regression fixtures.

Crush uses the four crossfaded combs and 0.75 feedback/0.7 return gain described above, with HP4 at 60 Hz on its return. Its [validation record](../research/audio/measurements/2026-10-26-crush-validation-48k.json) contains 54 passing static comparisons, including fresh stereo probes, crossfaded Sub1 positions, 90/128/137 BPM and clock-boundary impulses. Worst checked per-channel RMS error is about 0.021%; separate tails also pass. Eight native VST3 cases pass, including button-off. Initial host controls now seed engine smoothers before the first callback, so restoration before or after preparation gives the same settled hold phase.

```sh
uv run --locked python -m tools.rmx_crush_identify capture \
  --host /path/to/Intel/RMXReferenceHost --plugin /path/to/RMX-1000Plug-in.vst \
  --session build/artifacts/research/crush-reference
uv run --locked python -m tools.rmx_crush_identify identify \
  --session build/artifacts/research/crush-reference \
  --clock-session build/artifacts/research/crush-reference \
  --calibration calibration-reviewed.json --report build/artifacts/research/crush-identification.json
uv run --locked python -m tools.rmx_filter_match \
  --session build/artifacts/research/crush-reference --renderer build/rmx_render \
  --calibration calibration-reviewed.json --output build/artifacts/research/crush-candidate
```

The recipe labels immediate-start noise as diagnostic rather than a static pass. Original output differs during its first host block across block sizes; the checked 128-frame and 256-frame startup regions are excluded from its settled block-repeatability claim. Immediate nonzero startup, moving controls, effect switching, overload, other widths/rates and Sub2 modulation remain unmatched. Event plans still require native-host validation. Vendor recordings remain outside Git.

## Spiral: characterization and outer return component

The [identification record](../research/audio/measurements/2026-10-26-spiral-identification.json) records diagnostics from 106 selected captures in a 192-capture campaign. Factory Up/Down were tested at 48 kHz using impulses, separated and simultaneous channels, tone levels, input phase, DC-biased tones, binary noise and independent stereo probes. Repeated checked pulse captures are bit-exact. Wet superposition fails, and changing only the right input changes the left wet level substantially. A positive DC-biased tone has almost no late wet output. These observations constrain the generator; they do not identify its architecture.

At Main raw 128 and Sub2 zero, initial wet onsets are 1,792 frames for Up and 640 for Down, in addition to the independently established 32-frame bypass latency. Up retains unity dry gain at measured Main positions; Down's measured dry law is `clamp((255-rawMain)/126,0,1)`. Dominant tone frequencies and attack-envelope fits are diagnostics, not a validated pitch or envelope model. The production pitch generator remains the earlier approximation.

The outer return is separately identified: four independent unfiltered combs at quarter/half/three-quarter/one beat, feedback 0.75, send gain −3 dB, return gain 0.7, and the same adjacent Sub1 crossfade and whole-millisecond beat clock as Filter/Crush Echo. `FactoryEchoReturn.h` shares that implementation while retaining their respective 284/60 Hz return filters. Its Spiral profile is available to the component probe; it is not connected to the unmatched production pitch generator.

Thirty-two [component comparisons](../research/audio/measurements/2026-10-26-spiral-return-validation-48k.json) pass: sixteen impulse cases and sixteen independent stereo-probe cases at 120/137 BPM, including Main 113 and Sub1 positions excluded from fitting. Worst checked per-channel relative RMS error is 0.000047%. **The component input is the original plug-in's measured pitch stream. This does not validate a clone Spiral generator or the full effect.** No gain or wet-delay fitting is used. Four complete BPF/HPF/LPF/Crush renders remain bit-identical after extracting the shared component.

Reproduce with an independently obtained original bundle and reviewed bypass calibration:

```sh
uv run --locked python -m tools.rmx_spiral_characterize capture \
  --host /path/to/Intel/RMXReferenceHost --plugin /path/to/RMX-1000Plug-in.vst \
  --session build/artifacts/research/spiral-identification
uv run --locked python -m tools.rmx_spiral_characterize analyze \
  --session build/artifacts/research/spiral-identification \
  --calibration calibration-reviewed.json --report build/artifacts/research/spiral-identification.json
uv run --locked python -m tools.rmx_spiral_return capture \
  --host /path/to/Intel/RMXReferenceHost --plugin /path/to/RMX-1000Plug-in.vst \
  --session build/artifacts/research/spiral-return-impulses --main 128 --bpm 120 \
  --times 32 64 96 128 160 192 224 255 --stimulus impulses
uv run --locked python -m tools.rmx_spiral_return capture \
  --host /path/to/Intel/RMXReferenceHost --plugin /path/to/RMX-1000Plug-in.vst \
  --session build/artifacts/research/spiral-return-probe
cmake --build build --target rmx_spiral_return_probe
uv run --locked python -m tools.rmx_spiral_return compare \
  --session build/artifacts/research/spiral-return-impulses \
  --session build/artifacts/research/spiral-return-probe \
  --renderer build/rmx_spiral_return_probe --calibration calibration-reviewed.json \
  --output build/artifacts/research/spiral-return-candidate
```

Capture destinations and reports must be new. The characterization matrix writes substantial local audio and takes several minutes. Its stages can also be captured independently with `--stage`; combine their directories using the analyzer's six stage arguments. `--legacy-initial` permits the recorded initial campaign's naming convention for component comparison. Both analyzers verify reference identity and input/output/plan hashes. All raw vendor audio and binaries stay outside Git. Shared amplitude detection, pitch/phase reconstruction, Main mapping, inner feedback, other Sub2 positions, profiles, gestures and full-effect validation remain outstanding.

Further [Spiral core experiments](../research/audio/spiral-core.md) separate linked peak detection and input clipping from quiet linear feedback. `tools.rmx_spiral_core` captures and verifies 94 component recipes plus three long-clock/broadband captures. A quiet 34-second recording identifies fractional-clock reversals. `tools.rmx_spiral_envelope` adds 135 verified probes for shared activity and stepped threshold release, with numerical tools that need only the locked NumPy dependency. Its rejected exact binary-gate prediction is preserved. The research candidate passes 150 of the original 208 complete renders and 273 of the expanded 343. The latest [361-render audit](../research/audio/measurements/2026-10-27-spiral-robustness-prototype-48k.json) adds 18 captures: 285 pass and 76 fail, with no changed outcomes on the earlier 343. Production Spiral remains unmatched. Use `clock` for the scoped quiet-channel analysis, the envelope tool's `identify`/`tail` commands for component inference and repeated core `compare --session` arguments for complete-render sweeps.

`tools.rmx_spiral_robustness` reproduces original input-sensitivity, quiet-scaling, gate-refinement, feedback-collision and conditioned-recurrence diagnostics. The [audit](../research/audio/measurements/2026-10-27-spiral-robustness-audit.json) preserves failed prospective predictions and the failed autonomous comparison. Original late Up tails diverge after a one-ULP input change even though identical-input repeats are bit-exact. Supplying reconstructed original state to a recurrence is a component diagnostic, not a complete clone. Neither observation changes the one-percent whole/wet per-channel gate or establishes perceptual similarity. See the core research page for recipes and command examples.

## Reverb: identification and failed production baseline

The [88-capture identification record](../research/audio/measurements/2026-10-27-reverb-identification.json) separates initial repeatability/linearity, prospective Main timing, long Sub1 decay and output-filter validation. Both directions repeat bit-exactly at the initial fixed controls. Main moves the first reflection, and Sub1 zero still produces a roughly one-second decay. Long-tail measurements reach approximately 45.53/49.98-second broadband T60 extrapolations for Up/Down at Sub1 maximum. The complete model remains unfinished; the neutral-setting Down candidate below is a later checkpoint.

The fixed Sub2 model is a second-order high-pass for Up and low-pass for Down, with cutoff and output-level maps recorded in the measurement. Twelve fresh component comparisons pass, including stereo broadband input; worst wet-channel RMS error is about 0.0017%. **The original neutral-filter reverb supplies the component input. This does not validate a clone reverberator.** The [56-case production baseline](../research/audio/measurements/2026-10-27-reverb-production-baseline-48k.json) fails all 52 active, non-silent cases. Only Main-zero and silent fixtures pass. No production DSP change accompanies this checkpoint.

Start a new local campaign with a separately obtained original:

```sh
uv run --locked python -m tools.rmx_reverb_characterize capture --stage initial \
  --host /path/to/Intel/RMXReferenceHost --plugin /path/to/RMX-1000Plug-in.vst \
  --session captures/reverb/initial
uv run --locked python -m tools.rmx_reverb_characterize analyze \
  --session captures/reverb/initial --calibration calibration-reviewed.json \
  --report build/artifacts/research/reverb-initial.json
uv run --locked python -m tools.rmx_reverb_characterize predict \
  --initial build/artifacts/research/reverb-initial.json \
  --report build/artifacts/research/reverb-onset-predictions.json
uv run --locked python -m tools.rmx_reverb_characterize filter-model \
  --session captures/reverb/initial --calibration calibration-reviewed.json \
  --report build/artifacts/research/reverb-filter-model.json
```

Capture `--stage timing` into `captures/reverb/timing` with `--prediction build/artifacts/research/reverb-onset-predictions.json`. Capture `--stage filters` into `captures/reverb/filters` with `--prediction build/artifacts/research/reverb-filter-model.json`. Each capture also needs the same host/plugin arguments. The capture manifest binds the prospective file's hash before validation. Capture `--stage long-tail` into `captures/reverb/long-tail` without a prediction argument. This adds 16, 12 and four captures respectively; long-tail cases render 90 post-input seconds. Every stage supports `verify --stage STAGE --session DIRECTORY --report NEW.json` for exact samples, controls, extent and provenance.

```sh
uv run --locked python -m tools.rmx_reverb_characterize timing \
  --session captures/reverb/timing --prediction build/artifacts/research/reverb-onset-predictions.json \
  --calibration calibration-reviewed.json --report build/artifacts/research/reverb-onset-validation.json
uv run --locked python -m tools.rmx_reverb_characterize filter-validate \
  --session captures/reverb/filters --initial captures/reverb/initial \
  --model build/artifacts/research/reverb-filter-model.json \
  --calibration calibration-reviewed.json --report build/artifacts/research/reverb-filter-validation.json
uv run --locked python -m tools.rmx_reverb_characterize long-tail \
  --session captures/reverb/long-tail --calibration calibration-reviewed.json \
  --report build/artifacts/research/reverb-long-tail.json
cmake --build build --target rmx_render
uv run --locked python -m tools.rmx_reverb_characterize compare --stage initial \
  --session captures/reverb/initial --renderer build/rmx_render \
  --calibration calibration-reviewed.json --output build/artifacts/research/reverb-production-baseline
```

Reports and output/session directories must be new. Timing and filter validators return 1 when their declared component screen fails. The current complete production comparison intentionally returns 1 and preserves every failure. It applies only the independently reviewed 32-frame bypass offset and checks whole output and post-input tail separately per channel, without gain fitting or a wet alignment search. Analysis uses the locked NumPy dependency. Component results, complete-render results and listening/hardware equivalence remain separate.

### Autonomous Down network at Main128/Sub1-128

The later [network identifier](../tools/rmx_reverb_network.py) detects five comb pairs from independently excited left/right impulses. It fits ten feedback gains and a shared wet gain, with empirical filter and allpass hypotheses. The [standalone C++ candidate](../research/audio/experiments/reverb_down_neutral_probe.cpp) produces its own reverb from the input WAV. It uses no original-derived wet fixture. The [28-render report](../research/audio/measurements/2026-10-27-reverb-down-network-prototype-48k.json) passes separate whole/wet/tail screens, including eight fresh captures after freezing the model. Worst wet/tail errors are approximately 0.0047%/0.0056%.

```sh
uv run --locked python -m tools.rmx_reverb_network identify \
  --initial captures/reverb/initial --calibration calibration-reviewed.json \
  --report build/artifacts/research/reverb-down-network.json \
  --header build/artifacts/research/ReverbDownNeutralCalibration.h
cmake --build build --target rmx_core
c++ -std=c++20 -O2 -Wall -Wextra -Wpedantic -I include \
  research/audio/experiments/reverb_down_neutral_probe.cpp build/librmx_core.a \
  -o build/reverb-down-neutral-probe
uv run --locked python -m tools.rmx_reverb_network capture \
  --host /path/to/Intel/RMXReferenceHost --plugin /path/to/RMX-1000Plug-in.vst \
  --session captures/reverb/network-holdout --calibration calibration-reviewed.json \
  --model build/artifacts/research/reverb-down-network.json
uv run --locked python -m tools.rmx_reverb_network verify \
  --session captures/reverb/network-holdout --report build/artifacts/research/reverb-down-holdout-recipes.json
uv run --locked python -m tools.rmx_reverb_network compare \
  --initial captures/reverb/initial --filters captures/reverb/filters \
  --holdout captures/reverb/network-holdout --renderer build/reverb-down-neutral-probe \
  --model build/artifacts/research/reverb-down-network.json \
  --calibration calibration-reviewed.json --output build/artifacts/research/reverb-down-autonomous
```

The generated header is a new artifact, not an automatic overwrite of the [committed neutral calibration](../research/audio/experiments/ReverbDownNeutralCalibration.h) used by the compiled fixture. Compare them before evaluating a recalibration. The renderer's legacy form `INPUT NEW_OUTPUT SUB2_RAW TAIL_SECONDS` fixes Down Main128/Sub1-128 at 48 kHz. The extended form below uses measured static control maps. The comparison includes calibration/repeat and silent-control fixtures; each case's relationship to fitting is annotated in the published report. The prospective capture manifest binds the frozen model's hash. The one-percent gate, bypass-only alignment and separate whole/wet/tail checks remain unchanged.

### Static integer control maps and their interaction

The [current research candidate](../research/audio/measurements/2026-10-27-reverb-down-control-interaction-prototype-48k.json) passes 1,204 complete Down renders at factory settings, 48 kHz and 120 BPM. The count includes 1,024 control-calibration cases, 64 earlier mixed-development cases, 64 fresh prospective mixed cases and 52 prior fixtures. Worst wet/tail errors are about 0.0058%/0.0060%. A previous separable level model failed 14 mixed cases; its [report](../research/audio/measurements/2026-10-27-reverb-down-control-separable-prototype-48k.json) and source checkpoint `9364cfd` are retained. The correction is a fixed rank-two Main/Sub1 level map derived from two additional sweeps. Main delays use their measured integer values; a smooth quadratic misses the Main143 boundary.

`tools.rmx_reverb_controls` supports `capture`, `verify` and `identify` for four stages, each with 256 recipes: `main` (Sub1-128), `amount` (Main128), `main-long` (Sub1-255) and `amount-large` (Main255). Reports, session directories and generated headers must be new. Use the locally generated neutral network report from the preceding section, bound to the same reviewed calibration:

```sh
uv run --locked python -m tools.rmx_reverb_controls capture --stage main \
  --host /path/to/Intel/RMXReferenceHost --plugin /path/to/RMX-1000Plug-in.vst \
  --neutral build/artifacts/research/reverb-down-network.json --calibration calibration-reviewed.json \
  --session captures/reverb/control-main
uv run --locked python -m tools.rmx_reverb_controls verify --stage main \
  --session captures/reverb/control-main --report build/artifacts/research/reverb-main-recipes.json
uv run --locked python -m tools.rmx_reverb_controls identify --stage main \
  --session captures/reverb/control-main --neutral build/artifacts/research/reverb-down-network.json \
  --calibration calibration-reviewed.json --report build/artifacts/research/reverb-main.json
```

Repeat for `amount` using separate paths and a `reverb-amount.json` identification report. Build the initial separable hypothesis with `tools.rmx_reverb_control_model build --main MAIN.json --amount AMOUNT.json --calibration CALIBRATION.json --report SEPARABLE.json --header NEW_HEADER.h`. Then capture and identify `main-long` and `amount-large` with the same neutral/calibration arguments plus `--static-model SEPARABLE.json`. `verify` still requires only stage, session and a new report. The saved feedback predictions are checked separately from fitting; a failed prediction prevents model construction. Exponential weighting is used only for identification of finite recordings, never for complete-render acceptance.

```sh
uv run --locked python -m tools.rmx_reverb_control_model build \
  --main build/artifacts/research/reverb-main.json --amount build/artifacts/research/reverb-amount.json \
  --main-long build/artifacts/research/reverb-main-long.json \
  --amount-large build/artifacts/research/reverb-amount-large.json \
  --calibration calibration-reviewed.json --report build/artifacts/research/reverb-control-model.json \
  --header build/artifacts/research/ReverbDownControlCalibration.h
```

The comparator checks the model against the [committed control header](../research/audio/experiments/ReverbDownControlCalibration.h). For a recalibration, review and deliberately replace that header before rebuilding the C++ fixture with the preceding compiler command. Its extended CLI is `INPUT NEW_OUTPUT MAIN_RAW SUB1_RAW SUB2_RAW TAIL_SECONDS`. Controls must be integers 0–255; the legacy neutral form remains available.

```sh
uv run --locked python -m tools.rmx_reverb_control_model capture --recipe mixed-v2 \
  --host /path/to/Intel/RMXReferenceHost --plugin /path/to/RMX-1000Plug-in.vst \
  --model build/artifacts/research/reverb-control-model.json --calibration calibration-reviewed.json \
  --session captures/reverb/control-mixed-v2
uv run --locked python -m tools.rmx_reverb_control_model verify --recipe mixed-v2 \
  --session captures/reverb/control-mixed-v2 --report build/artifacts/research/reverb-mixed-v2-recipes.json
uv run --locked python -m tools.rmx_reverb_control_model compare \
  --model build/artifacts/research/reverb-control-model.json --calibration calibration-reviewed.json \
  --renderer build/reverb-down-neutral-probe --session main captures/reverb/control-main \
  --session amount captures/reverb/control-amount --session mixed-v2 captures/reverb/control-mixed-v2 \
  --output build/artifacts/research/reverb-control-comparison
```

Add `main-long`, `amount-large`, `initial`, `timing`, `long-tail`, `filters`, `neutral-holdout` and `mixed-development` session pairs to reproduce the full matrix. `mixed-development` labels the earlier mixed data used to diagnose the failed model; it does not claim prospective independence for the correction. `mixed-v2` requires the new frozen model's hash. All comparisons check unscaled whole/wet/tail output per channel with the reviewed bypass offset. Up is listed as out of scope. Production integration, fractional/moving controls, activation/bypass, other profiles/rates/tempos, overload, listening and hardware remain unfinished.

## Noise identification and statistics

Noise is independently excited in stereo. Repeated original renders after the documented activation event were bit-exact, but this project uses its own random generator. A sample null is therefore not its acceptance test. Common-seed original outputs identify a third-order filter with a fixed `(1-z^-2)` numerator. Twenty-one Main positions calibrate its coefficients/gain; a shape-preserving cubic interpolates them. Four additional positions differ by at most about 0.082 dB in the identified transfer response. These measurements are retained in the [filter identification report](../research/audio/measurements/2026-10-26-noise-filter.json).

The measured half-beat echo adds a first return of 0.35 and recirculates at 0.5. Default Sub1 endpoints imply −18/+6 dB; raw 124–131 is the centre deadband, with linear amplitude spans from raw 3 to 124 and 131 to 252. The calibrated path applies at 48 kHz with Normal width and modulation mode; other widths/resonance/rates retain the earlier project model and remain unmatched.

To reproduce coefficient identification with a separately obtained original:

```sh
uv run --locked python -m tools.rmx_noise_identify --capture \
  --host /path/to/Intel/RMXReferenceHost --plugin /path/to/RMX-1000Plug-in.vst \
  --session build/artifacts/research/noise-reference
uv run --locked python -m tools.rmx_noise_identify \
  --session build/artifacts/research/noise-reference \
  --report build/artifacts/research/noise-identification.json \
  --header build/artifacts/research/NoiseCalibration.h
```

Use a fresh report/header path. The generated header contains numerical calibration data, not original recordings or the manufacturer's random generator.

Long native-VST3 validation used 600 stationary seconds per case at Main raw 17, 81, 147 and 233, Sub1 raw 64, Sub2 zero and 120 BPM. All meaningful per-channel third-octave intervals fit inside ±0.5 dB; whole-level intervals fit inside ±0.1 dB. The largest measured whole-level difference was about 0.044 dB. Intervals are approximate 99% engineering screens, with a conservative multiplier and block-correlation correction; they are not listening evidence or a percentage of perceived similarity. Initial 120-second runs were inconclusive in some quiet bands. Extending duration narrowed uncertainty without changing the acceptance margins, and the shared capture prefixes remained bit-exact. See the [complete statistical record](../research/audio/measurements/2026-10-26-noise-validation-48k.json).

For an independently reviewed integer bypass calibration:

```sh
uv run --locked python -m tools.noise_statistics original.wav candidate.wav \
  --start 2 --duration 600 --calibration calibration-reviewed.json --report statistics.json
```

The interval must be stationary, and both channels must contain noise. A `pass` requires equivalence intervals inside the margins. `inconclusive` means the evidence does not establish equivalence or a difference beyond the margin; it is not a pass. Modulation, resonance, gestures, other levels/tempos, overload, hardware and listening equivalence remain outstanding.

## Build the offline host

`RMXReferenceHost` opens one explicit AU, VST2 or VST3 bundle, never a live audio device. It inspects parameter IDs and names and renders WAV probes with sample-timestamped parameter/MIDI events and a constant BPM transport. Modern Audio Unit bundles are registered only within the host process; they are not installed in a user or system plug-in folder.

Use the existing JUCE 8.0.6 checkout or allow the normal CMake JUCE fetch:

```sh
uv run --locked cmake -S . -B build/reference-host \
  -DCMAKE_BUILD_TYPE=Release \
  -DRMX_BUILD_REFERENCE_HOST=ON \
  -DRMX_JUCE_PATH=/path/to/JUCE-8.0.6
cmake --build build/reference-host --target RMXReferenceHost --parallel 4
```

The single-configuration executable is `build/reference-host/RMXReferenceHost_artefacts/Release/RMXReferenceHost`. Match the host architecture to the reference plug-in. AU and the minimal VST2 bundle adapter are available on macOS; VST2 currently supports one stereo float-replacing instance and short MIDI messages, without an editor or Steinberg SDK. Build an Intel host separately with `-DCMAKE_OSX_ARCHITECTURES=x86_64`. The source tree's original `RMXPluginProbe` remains a separate project-specific smoke checker.

In a fresh session directory, obtain an inventory:

```sh
build/reference-host/RMXReferenceHost_artefacts/Release/RMXReferenceHost \
  inventory /absolute/path/Reference.component > inventory.json
```

The inventory records identity, version, normalized parameter values, names, IDs and SHA-256 hashes of bundle files. For an already registered legacy AU, the optional `--registered-au AudioUnit:Effects/type,subtype,manufacturer` selects its public registry identifier; the host then requires the supplied bundle executable to appear in its actual loaded-image list. This rejects a registry selection that loads a different file. It does not register or repair an unavailable legacy component. A parameter's normalized 0..1 value is not necessarily its displayed frequency, gain or physical knob position. Map controls against the reference before treating two settings as equivalent.

## Capture a configured plug-in

A JSON plan must name the exact plug-in and version returned by inventory:

```json
{
  "schema_version": 1,
  "kind": "audio-plugin-capture-plan",
  "role": "reference",
  "expected_plugin": {
    "name": "EXACT NAME FROM INVENTORY",
    "manufacturer": "EXACT MANUFACTURER FROM INVENTORY",
    "version": "EXACT VERSION FROM INVENTORY"
  },
  "sample_rate": 48000,
  "bpm": 120,
  "tail_seconds": 20,
  "parameters": [],
  "events": []
}
```

An empty parameter list captures the plug-in's actual initial state; it does not establish a factory Default profile. Set controls explicitly or supply a known native state. Each initial parameter or parameter event requires `index`, `id`, `name` and normalized `value` from the inventory. The host rejects mismatching identities rather than guessing by position. A parameter event additionally uses `"type": "parameter"` and an integer `frame`. MIDI events use `"type": "midi"`, `frame` and a byte array such as `[144, 36, 127]`. Events must be ordered and fall inside the complete input-plus-tail interval.

Verify actual state and output rather than assuming a request took effect. For example, original Noise selection during initialization read back off and produced no noise. A button event after processing began activated it successfully. An initialization-only silent capture is therefore not valid evidence about Noise's sound or routing.

For example, an event at frame 48001 happens after one second plus one sample at 48 kHz, including any leading probe silence. The renderer splits processing at event boundaries; event timing is not rounded to the host block size. MIDI channel/status/data lengths are checked. This schedules host requests precisely; the plug-in's own smoothing, quantization and response remain part of the measured result.

An optional `initial_state` object can restore a previous host state snapshot:

```json
{"initial_state": {"path": "previous/state-before.bin", "sha256": "EXACT SHA256"}}
```

The state path is resolved relative to the plan file. The host verifies its hash, restores it after preparation/reset, then applies the explicit initial parameters. A remixbox export or `.aupreset` is not automatically the host's native state format. Convert/load it using the reference's supported workflow before recording a native state snapshot.

Render into a new directory:

```sh
build/reference-host/RMXReferenceHost_artefacts/Release/RMXReferenceHost \
  render /absolute/path/Reference.component probes/impulses.wav plan.json captures/echo-01 128 120
```

The final two optional numbers are maximum block size and watchdog seconds. The input must be stereo WAV; input and plan sample rates must match. No normalization, latency removal or sample-rate conversion is applied. The host checks input and output for non-finite samples. It preserves the full input and requested tail, including the plug-in's reported latency.

Each successful capture contains:

- `audio.wav`: stereo float32 output, including tail.
- `inventory.json` and `plan.json`: actual initial parameters, bundle identity/hashes and the requested timeline.
- `parameter-log.json` and `inventory-after.json`: immediate readback after every requested parameter change (initial requests use frame −1), plus final readable state. Immediate readback does not establish when the DSP responds.
- `state-before.bin` and `state-after.bin`: native plug-in state snapshots.
- `receipt.json`: completion, role, input/output/plan/state/host hashes, sample rate, frame count, block size, BPM, latency, tail and peak.

Roles are `reference`, `candidate` or `host_fixture`; every receipt identifies its origin as software. A role is a declared purpose, not verification of manufacturer authenticity or hardware equivalence. An existing capture directory is refused. A crash or failure leaves no successful completion receipt; retain the incomplete directory for diagnosis and use a new destination for retries.

The host permits up to 1,200 seconds of processing after the input ends, with events throughout that interval. This supports long noise statistics using a short silent input. Input WAVs remain limited to 180 seconds; the watchdog still bounds actual execution time. Use an explicit Noise-off event when measuring its tail.

## Calibrate the route before comparing effects

Use independent bypass captures with a broadband stimulus. The fractional estimator requires energy across many frequency bins; a sine cannot identify an unambiguous broadband delay. The existing `noise.wav` or separated impulse probe can be used with all effects disabled. Capture the full probe and tail without independent wet trimming.

```sh
uv run --locked python -m tools.fidelity calibrate \
  captures/reference-bypass.wav captures/candidate-bypass.wav \
  --report calibration.json
```

The result estimates integer and fractional route delay using correlation and cross-spectrum phase. It records per-channel polarity, channel disagreement, excited bandwidth and phase-fit residual. A positive delay means the candidate arrives later. A shared fixed-delay model must be eligible before it can be reviewed; low bandwidth, opposite polarity, mismatched channels or poor phase fit must be investigated.

Calibration starts with `verified: false`. Check the actual bypass settings, stable route, timestamps, clocks and diagnostics, then explicitly record `verified: true` in the reviewed calibration file. Eligibility is an automated screening result, not evidence that bypass was physically selected. This calibration estimates a fixed delay; it does not solve clock drift, time-varying latency or the whole converter transfer function. Never derive a separate calibration from each wet effect to improve its match.

## Compare deterministic cases

```sh
uv run --locked python -m tools.fidelity compare \
  captures/reference-echo.wav captures/candidate-echo.wav \
  --calibration calibration.json --mode deterministic \
  --maximum-relative-rms 0.01 --report echo-comparison.json
```

The tool requires reviewed, eligible calibration at the capture sample rate. It applies that delay only, using finite sinc interpolation for a fractional delay and discarding unsupported recording edges. It reports overlap and discarded frames. Each channel must have a measurable reference signal; silence is `not_assessable`, not an automatic pass.

`waveform_verdict` evaluates each channel's unscaled relative RMS error independently. A 0.01 tolerance means -40 dB error. The tool does not fit away gain or search the wet outputs for their best alignment. For example, half-amplitude audio has perfect correlation but fails with 0.5 relative RMS error. A `pass` establishes only the stated waveform criterion for those recordings, not a percentage of perceived similarity or full-device conformance. A failed deterministic waveform criterion returns exit code 1.

Spectral diagnostics include STFT magnitude error at several resolutions and third-octave average-energy differences. They are not a deconvolved transfer function, a perceptual model, an alias-rejection measurement or a substitute for transient and stereo analysis. Notches, insufficiently excited bands and noise floors need separate interpretation. Finite fractional interpolation can itself limit very high-frequency null depth.

For Noise or modulated late reverb, use `--mode stochastic`. The report remains `diagnostic_only` even for a numerically identical pair. Compare repeated-reference distributions and conduct the planned blind listening tests before adopting statistical acceptance limits.

## Measure stationary harmonic distortion

```sh
uv run --locked python -m tools.fidelity harmonics captures/drive-tone.wav \
  --fundamental 997 --start 2 --end 3 --report drive-harmonics.json
```

The chosen interval must contain a stationary known tone in both channels. Exclude attack, release and control movement. The analysis fits DC and sinusoidal harmonic components jointly and reports in-band harmonic levels and THD. It requires at least ten fundamental cycles and bounds the interval to five seconds / 262144 frames. THD+N, intermodulation and alias products are separate measurements.

## Verification and remaining work

Run the numerical regressions with `uv run --locked python -m tests.fidelity_tests`. They exercise known gain changes, integer/fractional delay, channel/polarity errors, narrowband rejection, a known cubic transfer and report preservation. CTest includes these as `reference_fidelity`.

For the native host fixture, build this project's VST3 with `RMX_BUILD_PLUGINS=ON`, then run:

```sh
uv run --locked python -m tests.reference_host_tests \
  --host build/reference-host/RMXReferenceHost_artefacts/Release/RMXReferenceHost \
  --plugin build/reference-host/RMXPlugin_artefacts/Release/VST3/RMX.vst3
```

Those tests validate the host, including event timing across block sizes and rejection of invalid capture plans. They never substitute the project plug-in for an original-unit reference. AU loading additionally depends on macOS component registration being available to the process.

Reference loading and the static fits described above are established for the scoped software settings. Sweep deconvolution, distortion-order separation, two-tone intermodulation, repeated stochastic acceptance, full control-map capture, listening tests and measured hardware validation still need implementation or reference data. The [capture manifest](reference-manifest.schema.json) remains the device/session provenance contract; native host receipts supplement it and do not automatically promote a session to reviewed.

The [moving-control investigation](../research/audio/measurements/2026-10-27-reverb-down-motion-characterization.json) now covers 61 original recordings with button changes, steps, ramps and host-block repeats. It confirms preserved button-off tails and separate button/knob timing paths. A first persistent-state candidate passes only 26/61 cases; [all failures](../research/audio/measurements/2026-10-27-reverb-down-motion-first-prototype-48k.json) are retained. Static agreement therefore does not yet justify integrating Reverb Down into production.

The [current motion checkpoint](../research/audio/reverb-down-motion.md) passes **56/77**, including all 16 cutoff-only and 14 Sub1-only motion cases. Eight Sub1 recordings are new prospective tests of its staged five-block control clock and separate directional level ramps. Their worst wet/tail/event-window errors are 0.1939%/0.1365%/0.0989% against unchanged 1% gates. The earlier cutoff checkpoint's worst fresh event window is 0.9928%, close to the limit. Twenty-one button/Main/combined failures remain. Independent bypass checks justify 32-frame audio latency without wet alignment fitting. Original-binary control-path inspection informed the Sub1 hypothesis; independent recordings verify it. This extends the standalone research candidate; production remains unchanged.
