# Reconstructing Random Noise modulation

1 November 2026. Random now moves the Noise filter cutoff using the measured target clock and ramp, replacing the previous amplitude approximation. The default modulation generator reproduces the Original plug-in's observed startup sequence. White-noise excitation remains independently generated.

The later [continuous study](noise-continuous.md), completed on 4 November, qualifies the remaining Wild/223 program over 7,140 stationary seconds with unchanged margins and 166,137 exact observed default targets. All three declared Random presets now have scoped qualifications across the two cohorts. The following 1 November result retains its original verdict.

Two of the three declared audio programs qualified at this checkpoint. The wide-filter program passes the whole-run spectrum/level, full conditional profile and late-section checks, but its early highest-control-bin right-channel level remains inconclusive. It stays unqualified. These are fixed User programs at48kHz/manual120BPM against RMX-1000 Plug-in2.2.0, not a hardware or whole-device accuracy percentage.

The [validation receipt](measurements/2026-11-01-noise-random-validation.json) connects the controls, numerical powers, independently recomputed statistics, preservation checks and signed-format delivery. Earlier [deterministic modulation](noise-control-fp.md) and [Sidechain](noise-sidechain.md) evidence retains its original verdicts.

## Measuring the clock and target ramp

The [read-only observer](experiments/noise_random_observer.py) records computed float control outputs, target changes, ramp steps and clock values from the installed Original plug-in. It never reads the manufacturer's integer PRNG state. Ordinary and observed captures must have identical complete audio, plan, initial/final state, parameter log and final inventory hashes. The Original executable is unchanged; its SHA256 is `dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced`.

The control law shares the deterministic modulator's operation-ordered period/depth arithmetic. Visible Sub2 is smoothed toward `max(raw−3,0)`, one count per sample. Period varies from9600 to approximately960 samples; depth rises by0.025 per smoothed count and saturates at1. Random tests its counter on16-sample boundaries against the integer period. A target is drawn when that boundary is reached, followed by a128-sample linear ramp and an exact target snap. The target is held until the next draw. The first processed Noise frame is4832 for the declared event at4800; the wrapper's32-frame latency places audible control motion at4864.

The production [NoiseModulator](../../src/core/NoiseModulator.cpp) implements this law and keeps a separate Random ramp phase. Scene calls the same out-of-line function as the CMake control probe, with floating-point contraction disabled. Random now enters the moving-filter path. Filter coefficients, stereo excitation, feedback return and existing qualification margins are unchanged.

Three discovery streams at raw11/43/223 and three fresh streams at4/117/255 cover547,008 float32 modulation values. All six complete streams match Original/native/ASAN exactly. The fresh conditional predictions were frozen before those observations using an earlier target prefix. That was evidence for the clock/ramp given those targets; it did not yet identify the default target generator. The final default generator also reproduces all six streams without supplied targets. Reversing the target sequence fails the control comparison.

## Inferring the repeating generator

Initial audio trials deliberately used an independent target generator. Three600-second and three completed1190-second cases remained inconclusive under the original independent-trajectory and self-stationarity gates. Their reports and powers are retained, rather than upgraded after changing the model.

The observed target prefixes repeated across Original instances. A two-word unsigned32-bit xor/add recurrence explains the sequence:

```text
output = signed32(second) / 2^31, rounded through float32
first = first xor second
second = (second + first) modulo 2^32
```

Startup was inferred from those float outputs. The first output corresponds to the exactly representable integer16,702,650, below2^24. The next float permits several nearby integer words. Enumerating its rounding cell and inverting the recurrence gives a unique first word1,193,046 that reproduces the994-draw discovery prefix. This uses computed control outputs, not captured PRNG memory, audio samples or executable code.

The [generator auditor](../../tools/audio/noise/rmx_noise_random_generator_audit.py) independently performs that inversion and compares its scalar recurrence and actual native/ASAN default generators with retained long Original target arrays of6571,10060 and27765 draws. These arrays share prefixes; their counts are not independent observations. The largest check covers27,765 consecutive targets. The production code stores the inferred startup words and recurrence, not a captured target table.

An optional borrowed target source exists for offline Engine diagnostics. It is installed only while stopped, owns no storage and is cleared by reset. The product uses the default generator. A prior supplied-target600-second filter experiment is retained as an inconclusive diagnostic. The final1190-second campaign passes no target file to the renderer and checks the actual default path.

## Comparing audio with the same control trajectory

Each final case freezes the native prediction before a fresh ordinary Original render. Native and ASAN complete WAV bytes agree. The fresh complete Original WAV must equal the earlier target-observed recording, and the current default target stream must equal the recorded Original targets. These prerequisites justify comparing two sources driven by the same nonperiodic modulation trajectory. They do not make the independent white-noise samples identical.

The overall point estimate remains the ratio of mean powers, `10log10(mean(candidate)/mean(reference))`. Its delta-method variance now includes covariance between the sources: the HAC variance of `candidate/mean(candidate) − reference/mean(reference)`. This removes shared trajectory variation from uncertainty without changing the estimand or margins. It would be inappropriate for the earlier independent-target trials; their conservative screens remain explicit.

Band margins remain0.5dB, whole-level margins0.1dB, with the−40dB meaningful-band floor, the same HAC correction and multiplier3. Ten-second conditional profiles divide each source into four control-value bins and six spectral bands. Full, early-third and late-third between-source comparisons must all pass, along with stereo correlation. Self-stationarity remains a diagnostic: the reconstructed finite random trajectory intentionally visits different target distributions in different sections. This differs from the initial independent-generator aggregate rule and is stated in the new report kind. No old verdict is silently overwritten.

At1190 stationary seconds per case:

| Width / Sub2 | Whole run | Full profile | Early / late overall | Early / late profile | Qualified |
| --- | --- | --- | --- | --- | --- |
| Mild /29 | Pass | Pass | Pass / Pass | Pass / Pass | Yes |
| Default /117 | Pass | Pass | Pass / Pass | Pass / Pass | Yes |
| Wild /223 | Pass | Pass | Pass / Pass | Inconclusive / Pass | No |

The independent [power auditor](../../tools/audio/noise/rmx_noise_random_reference_audit.py) uses separate float64 sums/einsum HAC arithmetic to recompute all intervals, profiles, subwindows, stereo and aggregate gates, and replays native/ASAN targets. Both overall and conditional-profile3dB gain negatives must fail. A tooling test also checks that covariance preserves the same power-ratio estimate under strong shared modulation and rejects a wrong gain. These checks establish the stated numerical comparisons; they do not replace listening.

## Reproducibility and delivery

Configure the normal and sanitizer builds, then build `rmx_noise_random_probe` and the existing Noise render/control targets. `uv run --locked python -m tools.audio.noise.rmx_noise_random_generator_audit --help`, `tools.audio.noise.rmx_noise_random_control_audit --help` and `tools.audio.noise.rmx_noise_random_reference_audit --help` list their inputs. Published JSON uses paths relative to the measurements directory for compressed powers. Historical independent-target exposure replay requires the initial model at commit `f3809f04f69c4e8431cb75c1700cc2c28b0427b8`; it must not use the new default generator.

One long debugger capture exceeded the host's default120-second wall watchdog. LLDB batch completion alone did not establish a completed render. Those attempts are rejected. The driver now explicitly checks all completion files before hashing them and uses the existing host's600-second watchdog option; the reference host executable and Original plug-in were not patched. The successful wide retry matches every required ordinary/observed artifact hash.

Current output bridges preserve34 prior non-Random short programs and all nine deterministic600-second WAVs.31 prior deterministic/Sidechain control streams remain exact. Eight native groups, two ASAN groups and nine Python tests pass. Firmware-host retains its inherited15/16 result, with `full_integration: Full engine factory path is silent`. The Engine is50,432 bytes and prepared audio buffers remain30,100,112 bytes; callback/reset allocation guards cover Random and Sidechain.

The signed AU/VST3 preview is checked separately against native decoded samples, including non-silent low and asymmetric input. Wrapper delivery does not qualify the wide Random audio case or the two remaining inconclusive Sidechain cases. Raw audio is generated serially within512MiB and deleted. Only compressed powers, scalar observations and small receipts are retained, with one current playable preview.

Remaining work includes the inconclusive early Wild/Random level, the two Sidechain audio cases, dynamic controls and mode switching, arbitrary music/source combinations, other rates/tempos, blind listening and physical hardware. Exact modulation controls do not establish an identical stochastic waveform or99% similarity across the device.
