# Measuring the RMX sound match

The [sound-matching research](../research/audio/rmx1000-fidelity.md) defines the overall target. Static factory Isolator and Echo pass the declared waveform criterion at 48 kHz. Default Noise also passes its statistical screen at four positions excluded from coefficient fitting. This does not certify a complete device sound match.

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

Reference loading and actual effect fitting remain open. Sweep deconvolution, distortion-order separation, two-tone intermodulation, repeated stochastic acceptance, full control-map capture, listening tests and measured hardware validation still need implementation or reference data. The [capture manifest](reference-manifest.schema.json) remains the device/session provenance contract; native host receipts supplement it and do not automatically promote a session to reviewed.
