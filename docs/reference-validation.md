# Reference measurements and release checks

We need recordings from a physical RMX-1000 before making claims about matching its sound. This workflow makes those recordings repeatable, keeps conversion delay separate from effect timing and produces measurements that can be reviewed alongside listening tests.

There are no hardware reference recordings in this repository. Generated probes, synthetic measurement tests and offline engine stress are software evidence only.

## Generate a session

From the repository root, with Python 3 and a built `rmx_render`:

```sh
python3 tools/reference_audio.py generate build/reference-session --rate 48000
python3 tools/reference_audio.py render build/reference-session/manifest.json build/reference-renders --renderer build/rmx_render
```

The output directory contains four deterministic, stereo, float32 WAV files, 17 static presets and a JSON capture plan. Rendering creates 68 wet files and `render-report.json`, including executable, preset, input manifest and output SHA-256 hashes. Rendering each file has a 120-second timeout. Use `--case echo` to render one case, or `--timeout 240` on a slower machine. Input hashes are checked before rendering.

Use a fresh directory for each session and render batch. Generation refuses a nonempty directory, rendering refuses existing selected audio/report files, and comparison reports are created exclusively. Existing captures and reports are preserved.

| Probe | Content | What to examine |
|---|---|---|
| `impulses.wav` | Left impulse at 2 s, right impulse at 6 s | Bypass latency, channel order, echo spacing, decay and stereo routing |
| `sweep.wav` | Identical stereo logarithmic sweep, 30 Hz to 18 kHz at 48 kHz, from 2 to 10 s | Filter shape by listening or a dedicated sweep analyzer, resonances and gain |
| `rhythm.wav` | Different pitched decaying pulses in each channel, 120 BPM from 2 to 10 s | Delay divisions, pitch change, rhythm and stereo behavior |
| `noise.wav` | Independent seeded white noise, from 2 to 10 s | Broad band levels, stereo width and continuous effect behavior |

Probes last 16 seconds by default. Use `--duration 60` to extend trailing silence for feedback or reverb tails. The renderer adds another four seconds. Comparisons use the overlapping duration and report uncompared frame counts. Record long enough that the effect reaches the measured noise floor; a truncated tail cannot support a decay-time claim.

The preset set covers neutral processing, all ten Scene FX and minimum/maximum positions for each Isolate band. These are starting points. Add cases for depth, resonance and Sub1 regions before deciding how close a particular effect is. Isolate modes with rhythmic actions, sampler triggering and Release FX require the event checks below. Static presets cannot test their transitions.

Every preset explicitly disables automatic tempo, sets 120 BPM, uses the external input as source and mutes the sampler. This removes several confounds. A normalized software value does not establish the matching physical knob position. Photograph and log the hardware's actual controls, including DEFAULT/USER settings.

## Capture the physical unit

1. Use one audio interface for playback and recording, with a shared clock. Disable normalization, automatic gain, warping, dither, noise suppression, effects and sample-rate conversion in the recording path. Save raw captures first.
2. Measure interface loopback and the RMX bypass route at the same rate, gains and cable routing. Begin below clipping and verify both input and output meters. Preserve the interface settings, firmware versions and a routing diagram in the capture folder.
3. Run `impulses.wav` through each bypass route. Record the full file with the same timeline origin. Confirm the left impulse precedes the right impulse by four seconds. Channel leakage and filtering must be inspected separately.
4. Capture each probe through the selected hardware setting at least three times. Keep unprocessed recordings, including silence before and after the signal. Never trim each wet recording independently to its first audible event.
5. Repeat software output through the same converters if comparing analog hardware with a software return. An in-memory render versus an analog capture includes the converters in the difference. Describe that difference in the report.
6. Fill in `manifest.json` captures using [the manifest schema](reference-manifest.schema.json). Keep the raw WAV hash, UTC timestamp, physical unit or software origin, case/stimulus IDs, exact setup, control log and bypass calibration report. Leave missing captures absent, with status `awaiting_reference` or `partial`.

The schema is a data contract; the tool checks its own generated paths and hashes but is not a general JSON Schema validator. Use a JSON Schema Draft 2020-12 validator when accepting capture submissions. Do not label the session `reviewed` until another person has checked the recordings and metadata.

## Calibrate route delay

The calibration command uses the strongest left/right peaks of the generated impulse probe. Run it on bypass captures only:

```sh
python3 tools/reference_audio.py calibrate build/reference-session/impulses.wav captures/software-bypass.wav --report build/software-route-delay.json
python3 tools/reference_audio.py calibrate build/reference-session/impulses.wav captures/hardware-bypass.wav --report build/hardware-route-delay.json
```

It reports each channel's integer delay and the change in left/right impulse interval. More than two frames of disagreement makes integer alignment unsuitable. This can indicate clock drift, channel latency differences, a changed recording origin or an unsuitable capture. Correct the capture setup and repeat. The interval diagnostic alone cannot distinguish these causes. A four-second probe also cannot establish long-session clock stability.

A positive delay means the candidate arrives later. For hardware as the comparison reference and software as the candidate, use `software_delay - hardware_delay` as `--candidate-delay-frames`. Human confirmation is required: the generated calibration report deliberately leaves `verified` false. Peak timing includes the converter's impulse response, so residual fractional-sample alignment error remains possible.

Do not estimate a new shift from each wet effect recording. That would hide the delay timing we are trying to measure.

## Compare

Example with a previously established candidate delay of 64 frames:

```sh
python3 tools/reference_audio.py compare captures/echo-impulses.wav build/reference-renders/echo--impulses.wav --candidate-delay-frames 64 --tail-start 6.005 --report build/echo-impulses-comparison.json
```

Both WAVs must have the same sample rate. Supported inputs are mono or stereo RIFF PCM16/24/32 and float32, including ordinary extensible PCM/float WAV. Mono is duplicated to stereo. Files are limited to 180 seconds and individual RIFF chunks to 256 MiB. Non-finite samples, truncated audio and invalid frame alignment are rejected. This is an offline Python tool, so 96 kHz band analysis can take time. Use `--skip-bands` for a quick timing/level pass.

| Measurement | Useful interpretation | Limit |
|---|---|---|
| Peak, RMS, DC and samples at unity | Level, offset and possible clipping | Peaks at unity do not prove clipping; the engine also has an intentional soft region above unity |
| First/last active envelope window | Coarse onset and audible-tail timing | 5 ms windows, threshold at 1% of each file's maximum envelope with an absolute floor |
| Separated envelope peak times | Approximate echo repeat spacing | Strongest 32 local maxima, at least 25 ms apart; not a transient detector for arbitrary music |
| Left/right level and correlation | Channel imbalance, mono collapse and stereo differences | Silent channels produce null correlation; some stereo effects intentionally decorrelate |
| Fixed bandpass RMS | Broad tonal differences | Overlapping Q=1 bands, not a deconvolved filter response; sweep energy is not flat per band |
| Sample/null error and fitted gain | Deterministic regression differences and gain offsets | Pitch modulation, converters, noise and fractional delay prevent clean nulls even for similar sounds |
| Tail decay fit | T20-style extrapolated RT60 from -5 to -25 dB integrated energy | Only useful for an isolated decaying impulse with enough tail above the noise floor; inspect fit R-squared and the waveform |

No overall score or pass/fail threshold is invented. Set per-effect tolerances after looking at repeated hardware captures. The repeatability floor determines which differences are meaningful. Match dry level and verify onset spacing first, then inspect spectral balance and decay. Keep both level-matched and unmodified files for listening, with the matching gain documented. Never overwrite the originals.

For sweep transfer functions, use an analyzer that implements the inverse sweep and compensation correctly. This tool reports band energies and does not claim to implement impulse-response deconvolution, THD, analog SNR or perceptual sound quality.

## Continuous offline engine stress

`rmx_soak` processes one persistent engine, with bounded buffers, variable block sizes from 1 to 1024 frames, stereo input, sampler triggering, input rolls, scene/isolate changes, bypass, Release FX and sequence clearing. It emits a JSON report and does not write hours of WAV audio.

```sh
cmake --build build --target rmx_soak
build/rmx_soak --seconds 7200 --rate 48000 > build/offline-soak-48k.json
```

Repeat at 44100, 88200 and 96000 Hz. Exit 1 means invalid arguments or non-finite output. Exit 2 means dropped engine events or output beyond the engine's bounded soft protection region of 1.25. Samples above unity are reported separately and may need output attenuation before a physical DAC or integer export. Deadline measurements are diagnostic: 1-frame calls expose overhead, desktop scheduling can interrupt a callback, and an accelerated offline pass does not measure device underruns.

Keep the report with the executable hash, exact source revision, compiler, operating system and machine details. A two-hour simulated run does not establish two hours of physical I/O, GUI stability, bounded total process memory or actual real-time scheduling. No memory leak claim is made from this tool.

Run the measurement-tool checks with:

```sh
python3 tests/reference_audio_tests.py
```

These checks verify known synthetic gain, integer shift, stereo polarity, exponential decay, RIFF decoding, non-finite rejection, calibration disagreement and reproducible fixture hashes. They do not compare the DSP with physical hardware.

## Release evidence checklist

Every row needs an evidence folder with date, machine/OS, exact executable hash, sample rate/block size, routing, observed result and relevant recording or log. Record failures and unexpected behavior. `Not run` is a valid status; it must not become a pass because the offline engine check succeeded.

| Area | Procedure | Evidence needed |
|---|---|---|
| AU and VST3 validation | Validate each release format with its platform/host validator and open it in a real supported DAW | Validator output, host/version, architecture and plugin binary hash |
| DAW state recall | Save/reopen a project containing non-default parameters, user samples and MIDI mappings; compare before/after | Project, sample inventory/hashes, parameter dump and recorded output |
| DAW automation | Automate every public control, tempo and bypass; test transport start/stop/seek, loop boundaries and automation during tails | Automation project, recorded output and documented sample offsets |
| DAW blocks and render | Test 32/64/128/256/512/1024 buffers, available supported rates and offline bounce; change rate/device safely | Settings log, bounce versus live capture, crash/underrun result |
| Rekordbox direct capture | Start/stop RMX repeatedly, grant/deny capture permission, restart rekordbox and change physical output | Screen recording, route logs, no doubled dry signal, direct sound restored after RMX exits |
| Real two-hour Mac session | Play representative music, exercise controls, load assets and switch presets with stable output | Start/end timestamps, CPU/memory samples, underrun counters, continuous output recording and any incident times |
| FLX4 | Test master/cue independently, all intended controls, connect/disconnect and reconnect | Actual routing diagram and recorded master/cue behavior; no assumed send/return |
| FLX6 | Repeat separately; device routing must not be inferred from FLX4 | Same evidence, controller/firmware and mapping version |
| AUTO and quantize | Test sparse, dense, syncopated and changing-tempo material; compare BPM and pad onset to known beat grid | Input files or licensed IDs, timestamps, phase/error plots, manual fallback behavior |
| X-Pad | Test all pads/banks, one-shots/loops, hold, overdub, delete/mute, input roll and different sample rates | Event log and output; verify loop pitch and tempo separately |
| Release actions | Exercise all three types from neutral and active scenes; release at multiple lever depths | Wet recording plus parameter states before/during/after, including keep/reset settings |
| Daisy hardware | Boot flashed board, verify codec/SDRAM/SD, process actual stereo I/O, controls, bypass and power cycles | Board revision, firmware hash, boot logs, measured latency, audio capture and memory/underrun counters |
| Recovery | Disconnect/reconnect device, missing sample files, invalid presets, suspend/resume and unexpectedly closed host | Reproduction steps, error message, recovered dry/output state and crash logs if any |

The DAW, physical RMX, FLX and Daisy rows require those environments. Cross-compiling firmware or building a plugin proves neither electrical operation nor host compatibility.
