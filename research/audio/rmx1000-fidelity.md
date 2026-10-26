# RMX-1000 sound matching research

- Updated: 2026-10-27
- Status: active; original plug-in captured, static Isolator/Echo/BPF/HPF/LPF/Crush/Noise fitted at 48 kHz; full-device validation incomplete
- Question: what evidence, DSP work and validation would support a defensible claim of very close RMX-1000 sound matching?
- Related implementation: [Scene](../../src/core/Scene.cpp), [Isolate](../../src/core/Isolator.cpp), [engine and Release](../../src/core/Engine.cpp), [drums](../../include/rmx/FactoryDrums.h), [capture tools](../../tools/reference_audio.py).
- Initial source audit revision: `5f1887fa9fbaa8b655b4a633b282121c802aba58`; linked manufacturer documents and papers were accessed on 2026-10-25. Implementation and numerical measurement updates below are dated 26–27 October 2026.

Controlled input/output measurement has now replaced several provisional DSP choices. Static factory Isolator, Echo and BPF/HPF/LPF/Crush Echo satisfy the declared waveform criterion against the original plug-in, and default Noise satisfies its statistical screen, within the scopes recorded below. The remaining effects and behaviors still use substantial project voicing. No full-device accuracy percentage or hardware equivalence has been established.

## What the primary evidence establishes

Pioneer's original [launch announcement](https://jpn.pioneer/ja/corp/news/press/index/1078) specifies 48 kHz processing, 24-bit converters, 20 Hz–20 kHz bandwidth, 0.005% THD, 102 dB S/N and 20 dB headroom. These are device specifications, not filter coefficients or effect algorithms. Start characterization at 48 kHz; resolve other host rates after the reference-rate behavior is understood.

The manufacturer-authored [operating manual](https://www.adamasyn.sk/subory/952.pdf), particularly pages 15–17 and 26, describes routing, control functions and effect behavior. Noise is generated white noise with filtering and echo. Spiral has separate controls for its delay, echo timing and pitch shift. Reverb's user controls include effect amount and output filtering. These descriptions constrain a model without identifying its numerical implementation. This PDF is a retailer-hosted copy of Pioneer's document.

The manufacturer-authored [remixbox manual](https://cf3.zzounds.com/media/RMX-1000_software_manual_remixbox_EN-7f81d750b47ca76a1b62fa66b08acabd.pdf), pages 12–14, provides the customization schema: four echo-time regions, filter widths, feedback characters, modulation/resonance choices, reverb sizes/times, per-mode crossover choices, drum gain/decay/envelope, asymmetric pitch ranges and Release settings. It does not publish the numerical values behind labels such as Default or Wild. Use the table to define coverage; measure the values. This is also a retailer-hosted manufacturer document.

Pioneer's [product-planner interview](https://blog.pioneerdj.com/pioneer-dj-history/from-efx-to-rmx-we-explore-the-evolution-of-our-dj-effectors/), RMX-1000 section, explains that the macro knobs were intentionally designed to produce a build-up through a simple left-to-right gesture. This supports treating the complete control trajectory as part of the sound, including intermediate positions and transitions.

Firmware version changes the target. Pioneer's [firmware history](https://downloads.support.alphatheta.com/firmwares/dj-effectors/RMX-1000/RMX-1000-Firmware-Change-History-Ver220-en.pdf) records changes to Spiral level, Back Spin fade-out, quantize/overdub and an Echo no-output fault. Capture firmware version, Default/User mode and the actual settings file for every session. Do not combine recordings of different revisions into one supposedly fixed target.

## The official plug-in as an initial reference

The [RMX-1000 Plug-in manual](https://www.eprodance.cz/user/documents/related_files/Pioneer/RMX_1000_manual_EN.pdf), pages 2–4, confirms that the plug-in runs in a compatible host, loads remixbox custom settings and can process audio without the physical RMX connected. It is a practical candidate for automated digital reference capture. Compatibility, installation, available formats and timing must be checked on the actual host; the manual does not establish support for this computer.

Use the plug-in to isolate algorithm behavior from analog converters. Record its binary version/hash, host version, sample rate, block size, reported latency, transport, reset method and exported settings. Verify repeated renders before assuming deterministic behavior. Noise, modulation phase, unreset delay state or host scheduling can prevent a sample null even when the same plug-in is rendered twice.

Treat a plug-in match and a physical-device match as separate milestones. Manufacturer descriptions of the same effects are not proof of bit-identical DSP or identical overload behavior. The eventual hardware comparison must include the analog path, connection-level setting and physical control response.

## Define the accuracy target before fitting

For a deterministic, repeatable signal with independently calibrated routing, define:

```text
relative RMS error = sqrt(sum((reference - candidate)^2) / sum(reference^2))
error dB = 20 * log10(relative RMS error)
```

A proposed strict engineering target is relative RMS error at or below 0.01, equivalent to -40 dB error. This is a definition of one-percent waveform error, not a universal definition of 99-percent perceived similarity. One-percent error energy instead corresponds to -20 dB and ten-percent relative RMS error. Report which quantity is used. Exclude silent references from the ratio and test their absolute noise separately.

Require absolute level, wet output and individual channels to pass their own checks. A strong dry path can conceal an incorrect effect in a whole-output metric. Where the measured routing permits it, characterize the direct and effect paths separately; do not subtract an assumed dry signal from an unknown topology.

The repository's comparator demonstrates why correlation cannot be the headline score. A synthetic 1 kHz sine reduced to half amplitude returns correlation 1.0 while its level and relative RMS error are both -6.0206 dB. Its gain-fitted residual is essentially zero. Gain fitting is useful for diagnosis but must not erase a level mismatch from acceptance.

Timing requires similar care. At 48 kHz, a one-sample shift of a 1 kHz sine gives 13.08% relative RMS error; at 10 kHz it gives 121.75%. These are analytical calculations, checked in Python. Establish fractional delay from independent bypass/calibration signals. Never optimize a separate shift for every wet recording: doing so can hide an incorrect echo or release onset.

For stochastic noise and modulated late reverb, compare repeated-reference distributions: averaged spectra, band envelopes, decay curves, stereo coherence and modulation statistics. A different random sequence should not automatically fail a waveform-null requirement. Conversely, similar long-term spectra cannot excuse wrong transients, routing or audible modulation.

Use blind listening as a second axis. [ITU-R BS.1116-3](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1116-3-201502-I!!PDF-E.pdf), section 4, specifies a double-blind triple-stimulus hidden-reference method for small impairments. [ITU-R BS.1534-3](https://www.itu.int/rec/R-REC-BS.1534-3-201510-I/en) addresses intermediate quality and is useful earlier when alternatives are clearly different. Neither scale is a percentage of sonic identity. Randomized ABX can supplement these tests; failing to achieve statistical significance alone does not prove equivalence. Predeclare a practical equivalence margin, analysis and stopping rule, and account for repeated trials within listeners.

## Findings in the current implementation

These are historical observations from the initial source audit and measurement priorities. The dated measurement updates below supersede their Isolator, Echo, Noise, BPF/HPF/LPF and Crush entries.

| Area | Current code | What must be identified |
| --- | --- | --- |
| Isolate crossover | First-order complementary split with default 250 Hz / 4 kHz settings; shared crossover controls | Reference slopes, phase, frequency choices by mode, gain/kill curves and band interaction |
| Cut and Gate | Project envelope detectors, thresholds, attack/release and kick extraction | Threshold versus input level, detector sidechain, retrigger behavior, pumping and frequency selectivity |
| Add, Trans and Roll | Project tap/rate tables and capture boundaries | Each pattern's actual tap times/gains, duty cycle, beat phase, boundary behavior and transitions |
| Echo family | Project cutoff/Q curves, feedback-character multipliers and hold threshold | Feedback-loop filtering versus output filtering, stereo topology, repeat gains, application ranges and complete knob maps |
| Noise | Identical generated source in both channels before downstream processing; 90 Hz–12.5 kHz sweep, project compensation and one-beat echo | Bandwidth, resonance, gain, stereo correlation, modulation destination, sidechain law and echo coloration |
| Spiral | Two crossfaded delay heads; one-octave endpoint, cosine weighting and project window sizes | Pitch trajectory, head/window topology, periodic artifacts, repeat-dependent pitch and feedback coloration |
| Reverb | Eight fixed delay lines, Householder mixing, one-pole damping and project T60 mapping | Early reflections, frequency-dependent decay, diffusion, density, stereo behavior and motion during macro changes |
| Crush | Rounded amplitude quantization followed by low-pass filtering | Quantizer law, signal-level dependence, possible sample holding/rate reduction, alias products and control law |
| Factory drums | Original synthesized kick, snare, clap and hat with project normalization and envelopes | Actual reference transient, spectrum, pitch contour, noise distribution, gain, decay and retrigger behavior |
| Release | Project Back Spin, Echo and Brake trajectories and lever thresholds | All lever regions, source capture, speed/time curves, fade, reset/keep logic and return-to-dry timing |
| Output | Linked sample-peak limiter at 0.9995 with 50 ms recovery | Reference overload transfer, level-dependent pumping and interaction with feedback and summed drums |

A specific reverb question needs resolution rather than an immediate code change. The launch description mentions reverb pitch/time movement, whereas the operating manual emphasizes effect amount and output filtering. The current code keeps room lengths independent of the Main macro. Capture sustained tones and impulses during Main sweeps to distinguish actual delay/pitch motion from filtering or increased wet level. Do not add a generic shimmer pitch shifter based solely on marketing wording.

The 27 October measurements below resolve the static timing part of this question: Main changes the measured reflection delays substantially. Moving-control pitch behavior and the reverberator topology remain unidentified.

There are multiple engine paths. The preserved [standalone runtime](../../hardware/runtime/src/core/SceneEffects.cpp) contains different Scene algorithms. The [F06 build](../../hardware/firmware/full_engine/CMakeLists.txt) compiles the maintained desktop Engine, Scene and Isolator sources directly. Calibrate the maintained engine first, identify which firmware variant is being evaluated, and keep desktop/embedded parity tests alongside later measured comparisons.

## Measurement campaign

### 1. Freeze the reference and establish repeatability

Use a known unit and firmware, one documented settings export and a fixed connection-level mode. Begin with Default, then add deliberately changed User cases. Capture photographs/control logs and asset hashes. Repeat representative captures at least three times before choosing tolerances; characterize variation in noise and modulation with more repetitions where necessary.

Measure interface loopback, reference bypass and candidate bypass with unchanged gain/cabling. Record absolute gain, polarity, channel order, fractional delay, impulse response, noise and crosstalk. Add independent timing markers throughout longer sessions. A shared interface clock does not make a separate hardware processor's internal clock identical. Apply any justified correction from calibration evidence only and retain the raw capture.

Compare digital reference against digital candidate first. For hardware comparisons, characterize the additional converter path explicitly or pass both candidates through equivalent conversion. An inverse filter that makes the waveform null can also erase real hardware character; distinguish diagnostic de-embedding from the delivered sound.

### 2. Identify stationary structures

Use channel-separated impulses, long exponential sine sweeps, stepped tones, two-tone inputs, independent noise, amplitude steps and silence. Acquire low-level linear responses before overload tests. Use measured analog levels as well as dBFS: interface gain and device connection mode can otherwise produce inconsistent operating points.

[Farina's swept-sine method](https://www.angelofarina.it/Public/Papers/134-AES00.PDF) separates linear response and harmonic contributions through deconvolution for suitable approximately time-invariant systems. Extend the existing sweep generator with an inverse filter and proper analysis before treating its recordings as transfer-function measurements. Freeze controls and modulation during this test; one impulse response cannot represent a time-varying, nonlinear effect under arbitrary input.

For Echo, estimate every repeat's delay, gain, spectral change and cross-channel leakage. In a simplified fixed feedback loop, repeat gain g and delay D imply T60 = -3D / log10(abs(g)). Use that relation as a diagnostic, not as proof of the reference topology. Filtering, saturation and mixed direct paths require richer fitting.

For Drive and Crush, measure harmonics, intermodulation and alias products at multiple levels and frequencies. A low-level frequency sweep alone cannot identify their nonlinear behavior. For Gate/Cut, include isolated kick, bass, mixed kick+bass, transient steps and sustained tones so detector dynamics are not fitted to only one musical example.

### 3. Map the controls and performance transitions

Begin with nine positions across each main continuous control, including endpoints and center; refine around abrupt transitions, hold boundaries and resonance peaks. Sweep one control with the others fixed, then add targeted interactions rather than an enormous uninformative Cartesian product. Log the physically observed position or MIDI value; equal normalized positions are not evidence of equal internal parameters.

Test at 80, 120 and 160 BPM initially, then extremes and triplets. Measure timing under manual tempo before AUTO/quantize so tracking errors do not contaminate delay identification. Capture slow sweeps, fast throws, effect changes with a live tail, on/off, retrigger, Panic, Release engagement and return. Add host block-size and sample-offset tests separately.

### 4. Capture the distinctive sources

For drums, start with four instruments times three decay choices times two envelopes: 24 settings at neutral pitch/gain, each with repeated isolated hits and sufficient silence. Then test pitch endpoints, intermediate bends, rapid rolls, overlapping instruments and level changes. Infer deterministic playback versus randomized generation from repeated captures. Do not assume an oscillator design or drum-machine ancestry from timbre alone.

For Noise, use silence at the input to isolate its generated source, then add rhythmic sidechain stimuli. For reverb, record long tails until the measured floor; compare octave-band decay, early energy, buildup, stereo correlation and modulation. For Spiral, use harmonic material, a stable tone and clicks to distinguish pitch motion from moving delay and to expose crossfade artifacts. For Release, use both sustained tones and rhythmic material at every lever region, starting from neutral and active effects.

### 5. Validate unseen material and combinations

Reserve complete input clips, control positions and tempos that are never used for fitting. Include percussion, vocals, sustained harmonics, bass-heavy material and dense mixes with suitable provenance. Split by source performance/session rather than adjacent windows of the same recording. Evaluate the full routing, including INPUT/X-PAD selection, scene+isolate combinations and Release during feedback tails. A model that matches isolated blocks can still fail when level or internal state interacts.

## Recommended modelling approach

Use a structured model with measured parameter maps: filters and curves for static response, explicit delays and pitch heads for timing, envelope detectors for dynamics and a fitted reverb network for tails. Fit in stages and retain a small held-out suite after every change. Prefer monotonic constrained curves for controls where measurements support monotonicity; retain discontinuities and hysteresis when the reference actually has them.

For reverb, fitting one broadband decay is insufficient. [Prawda, Välimäki and Schlecht](https://www.dafx.de/paper-archive/2019/DAFx2019_paper_46.pdf) study frequency-dependent decay control in feedback delay networks. Their method is relevant to matching damping once the target has been measured; it does not identify the RMX algorithm. The current eight-line architecture is a candidate, not a requirement. Change the topology if early reflections, density or modulation cannot be fitted adequately.

Use learned models selectively if a measured nonlinear block resists a compact model. [Wright, Damskägg and Välimäki](https://dafx.de/paper-archive/2019/DAFx2019_paper_43.pdf) demonstrate recurrent models for specific amplifiers/distortion devices. Their error-to-signal ratio is an energy ratio; reported percentages cannot be read as percent perceptual accuracy. This work does not establish that a small network can learn an entire tempo-synced RMX with long feedback memory, generated noise, state transitions and unseen controls. Benchmark any learned block on the actual embedded budget before adopting it.

Keep protective output behavior explicit. Begin matching below limiter activation, then characterize reference overload and candidate protection independently. A protection stage that changes normal operation becomes part of the measured difference. Preserve existing preset compatibility and expose reference-calibrated behavior separately from project extensions such as the wider pitch range.

## Acceptance proposal

These are proposed starting targets for review after reference repeatability is measured. They are not measured results or universal audibility thresholds.

| Dimension | Proposed initial criterion |
| --- | --- |
| Deterministic digital waveform | At most 1% relative RMS error after independently established calibration; require both whole-output and isolated-effect tests where meaningful |
| Level and filter response | Absolute level within 0.1 dB; band/transfer magnitude typically within 0.25 dB over declared passbands; inspect phase/group delay and excluded notches separately |
| Delay and events | Digital repeat/onset timing within one 48 kHz sample where reference behavior permits; fractional route calibration assessed independently; analog trigger distributions reported separately |
| Pitch | Within 2 cents for steady deterministic pitch tests; trajectories and transition artifacts evaluated separately |
| Reverb/noise | Band decay within 5% and averaged band level within 0.5 dB as initial screening; confidence intervals from repeated captures, stereo and transient checks, then listening |
| Controls and routing | Every documented mode and reset/source action covered; no missing Release or roll behavior hidden by an aggregate score |
| Listening | Blind hidden-reference assessment with a predeclared equivalence margin and confidence intervals; no claim of identity from a small nonsignificant ABX result |

The auxiliary limits are separate engineering screens and are not mathematically equivalent to one-percent waveform error. For example, 0.1 dB alone is about 1.16% amplitude difference. A deterministic case must satisfy its waveform criterion as well as the relevant screens. For stochastic cases, replace an invalid sample-null criterion with the specified statistical and listening evidence and label that distinction.

Do not average all settings into a single flattering number. Report per-effect coverage, worst cases, parameter-range exclusions, repeatability floor and confidence intervals. A possible future statement is that a named version meets specified tolerances on a published suite; the suite and capture provenance make that claim reviewable.

## Work to do next

1. Use the acquired official plug-in 2.2.0 for further digital characterization; obtain physical-unit captures for the final hardware target.
2. Extend the now-implemented [event/capture/fidelity workflow](../../docs/audio-matching.md) with remaining sweep, intermodulation, stereo/coherence and listening work. The earlier 17-preset/four-probe suite is only a seed.
3. Extend the fitted bypass/Isolator/Echo/Noise work to other profiles, transitions and rates. Preserve measured timing quirks and independently calibrated routing.
4. Fit the captured drums and remaining filter effects; then complete Spiral, Release, other Isolate modes, reverb and combined gestures against fresh data.
5. Validate the maintained desktop core, F06 embedded path, host rate conversion and physical input/output as separate stages. Preserve the existing real-time allocation, memory and correctness tests throughout.

Store raw captures and analysis output under `build/artifacts/research/` with hashes, settings, control logs and calibration metadata. Reference recordings used for analysis are not automatically cleared for redistribution as factory sample assets. Leave unmeasured cases marked as such in the [capture manifest](../../docs/reference-manifest.schema.json).

## Open questions

- A compatible official plug-in 2.2.0 is now captured. Can a physical RMX-1000 be measured, and which hardware/firmware version should be the final target?
- How repeatable are Noise, modulation, drums and reverb after a documented reset?
- Which control maps and defaults differ between the plug-in and hardware?
- Does reverb macro motion change delay/pitch or mainly filtering and wet amount?
- Which original behavior is required at overload, host rates other than 48 kHz and the extended project pitch range?
- Can measured matching fit the F06 CPU/memory deadline on a real board, including worst-case simultaneous effects?

## Implementation progress on 26 October 2026

The [offline capture and measurement workflow](../../docs/audio-matching.md) now has a native AU/VST3 host, sample-timestamped parameter/MIDI events, preserved state and hash receipts, fractional bypass calibration, per-channel unscaled waveform criteria, STFT/band diagnostics and stationary harmonic fitting. The host shares its process-local modern AU registration and transport implementation with the existing plug-in probe.

Thirty CTest groups passed, including twelve new known-signal numerical regressions. Seven native host tests passed with the current project VST3 and seven with the project AU. The project smoke probe also passed with all 152 parameters. A persistent host fixture under `build/artifacts/research/host-validation-2026-10-26/` demonstrates block-size invariance and correctly fails a known -6 dB level change. These remain project/synthetic checks.

The official Mac plug-in 2.2.0 was downloaded from AlphaTheta's support link; its installer notarization and bundle signatures verified using macOS trust services. Its Intel-only AU was unavailable to the modern registry on macOS 26.6.2. A minimal original public VST2 ABI adapter subsequently loaded the package's signed VST2 bundle successfully under Rosetta, without installer scripts or importing manufacturer DSP implementation.

Actual reference captures now establish a bit-exact digital bypass with 32 samples of unreported latency at 48 kHz. Static Isolator and Echo captures were bit-exact across checked host block sizes of 32, 128 and 256. At 44.1 and 96 kHz, bypass instead shows filtering and different latency, so those rates are excluded from the first fitted model.

Factory Isolator was identified as directly summed LP4 / HP4–LP4 / HP4 branches, with fitted crossovers near 284 and 4649.04 Hz. Its active centre has phase shift; disabling the section is a true dry bypass, even with non-neutral knobs. The measured full-kill/+6 dB knob law is linear in amplitude outside raw centre deadband 124–131. The engine now implements those findings and appends an explicit section-enable parameter while preserving earlier parameter indices and legacy preset routing.

Factory Echo preserves unity dry signal, has output amount `clamp((rawMain-3)/189,0,1)`, and uses quarter/half/three-quarter/one-beat divisions with static boundaries at raw 66, 132 and 194. Its output is high-passed with a second-order Butterworth response; Sub2 follows the fitted exponential cutoff described in the [DSP notes](../../docs/dsp-model.md). Repeats decay by approximately 0.7 in amplitude. These measured behaviors replace the earlier dry/wet crossfade, provisional beat defaults and filter map.

Independent validation uses stereo broadband, chirp, percussive and multitone signals, including mixed positions withheld from fitting. Thirty-five Isolator cases and twenty-five Echo cases at 120 BPM passed the one-percent unscaled per-channel RMS criterion, followed by another twenty-five Echo cases at 137 BPM. Numerical results and capture/renderer hashes are retained in the [48 kHz measurement summary](measurements/2026-10-26-factory-48k.json). No gain matching or wet delay search was used. The [reproduction recipe](../../docs/audio-matching.md) preserves raw recordings locally and checks file hashes before comparison.

Further clock measurements show that synchronized Echo and Noise truncate the beat period to whole milliseconds before applying the delay division. At 128 BPM the half-beat delay is 11,232 frames at 48 kHz, instead of the ideal 11,250. Integer and fractional BPM captures support this map. Original Auto-off holds manual tempo; Auto-on follows the supplied host tempo. The clone's plug-in now follows that selection, and resting controls match the original inventory. The [clock record](measurements/2026-10-26-clock-48k.json) retains the observations and impulse comparisons.

Noise was then activated using a processing-time button event; initialization-only requests had read back off. Its original output is independently excited in stereo and repeatable after the same reset. Common-seed captures identify a third-order filter with a fixed differencing numerator. The project now uses that fitted response with its own stereo generator, the measured −18/+6 dB level span/deadband, and a half-beat echo with 0.35 first return and 0.5 feedback. Four positions excluded from coefficient fitting pass the [600-second statistical screen](measurements/2026-10-26-noise-validation-48k.json) at Default/Normal width, Sub2 zero, 48 kHz and 120 BPM. This is statistical response evidence, not a sample null or listening result.

Further filter captures identify BPF's direct additive band-pass and its 0.85 band contribution to the echo feed. HPF/LPF replace the direct path, using delayed, first-order-filtered band-pass resonance feedback around a Butterworth biquad. Their echo returns share HP4 filtering at approximately 284 Hz, 0.75 comb feedback and 0.7 output gain. Sub1 continuously crossfades between adjacent quarter/half/three-quarter/one-beat delays; the standalone Echo instead selects discrete times. Button-off preserves their existing tails.

The engine now implements those measured static factory paths. One hundred sixty-four comparisons pass the declared one-percent unscaled per-channel RMS criterion, including held-out stereo signals, separate tails and 137 BPM cases. Worst checked segment errors are about 0.0018% BPF, 0.0063% HPF and 0.16% LPF. Nine native VST3 cases also pass, including button-off. The [identification](measurements/2026-10-26-filter-identification.json), [validation](measurements/2026-10-26-filter-validation-48k.json) and [reproduction recipe](../../docs/audio-matching.md#bpf-hpf-and-lpf-echo) retain the scope and provenance. These checks cover Normal width, Sub2 zero and factory delay/feedback settings at 48 kHz; modulation/resonance profiles and gestures remain outstanding.

Crush then required continuous input and DC steps: isolated impulses can fall between held samples and falsely suggest a muted effect. Its measured path uses sample holding, a resonant high-pass filter and complementary dry/wet gains; no amplitude quantization is needed in these captures. The hold period depends on two float multiplications, beginning with a rounded reciprocal of 255. Several seemingly equivalent division/double formulas pick different input frames at repeated boundaries. Long direct-only noise, late impulses and fresh stereo probes resolved that difference. Its echo return uses HP4 at 60 Hz with the shared crossfaded comb structure.

The [Crush identification](measurements/2026-10-26-crush-identification.json) and [54-case validation](measurements/2026-10-26-crush-validation-48k.json) retain those findings. All checked static cases pass, including 90/128/137 BPM, separate tails and late boundaries, with worst per-channel RMS error about 0.021%. Eight native VST3 cases also pass, including button-off. Pre/post-prepare controls now give the same settled engine hold phase. Original immediate-start output differs within the first host block by block size and remains unmatched, along with moving controls, other widths/rates and modulation.

Spiral Up/Down now have a 192-capture identification campaign, with reproducible diagnostics from 106 selected captures in the [Spiral record](measurements/2026-10-26-spiral-identification.json). Deterministic repeated pulses contrast with failed wet superposition. An unchanged left input produces substantially different left wet levels when the right signal changes; DC-biased tones almost suppress the late wet output. Amplitude-normalized responses remain close across checked tone levels. These constrain a shared amplitude detector/pitch model but do not identify one.

The outer return is independently fitted as four unfiltered crossfaded combs, with −3 dB send, 0.75 feedback and 0.7 return gain. A reusable C++ component passes 32 comparisons using the original pitch stream as its fixture, including fresh stereo signals, held-out controls and 137 BPM. Worst checked per-channel RMS error is about 0.000047%. The [component validation](measurements/2026-10-26-spiral-return-validation-48k.json) explicitly excludes the inner generator and full Spiral effect; the production generator remains approximate.

The subsequent [core investigation](spiral-core.md) verifies 94 more input/control recipes and fits selected first-pass clipping and quiet feedback components. It identifies a linked 32-frame peak measurement, a 12 kHz input filter, a separate 12.1 kHz loop filter and slight neutral-clock drift. Three further captures expose long-clock reversals and validate stereo broadband tails. Correcting that clock and smoothing before peak hold raises the experimental candidate from 62 to 110 passes in a 208-render neutral-setting sweep, with no passing-case regressions. All 98 failures remain in the [expanded report](measurements/2026-10-26-spiral-neutral-clock-prototype-48k.json); the candidate is a research fixture and does not replace the production generator.

A further 135-capture envelope campaign identifies one-decibel release steps, a 151-block cadence, release-before-input-floor ordering and cancellation in the shared activity measurement. The [envelope checkpoint](measurements/2026-10-26-spiral-envelope-prototype-48k.json) passes 150 of the original 208 cases, including all 104 original Down cases, with no passing-case regressions. In the expanded 343-case set, 273 pass and 70 fail. A prospective exact binary-gate hypothesis fails three new checks and remains explicitly rejected in the [envelope record](measurements/2026-10-26-spiral-envelope-identification.json). The candidate uses the measured gate bracket instead. Remaining Up tails and an added Down diagnostic still prevent full Spiral fidelity or production adoption.

The [27 October robustness audit](measurements/2026-10-27-spiral-robustness-audit.json) adds 18 verified original captures. Identical-input Up repeats are bit-exact, but changing one left impulse by one float32 ULP makes the original late wet waveform diverge sharply. Quiet Up responses remain linear across eight orders of input amplitude in the checked unsaturated windows. A recurrence supplied with reconstructed original state fits closely and rejects altered-delay/gain controls; it does not produce an autonomous match. Two prospective feedback-timing models fail the same new collision probes. Only a narrower empirical activity-gate bracket is adopted. The [361 complete renders](measurements/2026-10-27-spiral-robustness-prototype-48k.json) yield 285 passes and 76 failures, with unchanged results on the preceding 343. Strong original sensitivity does not establish perceptual equivalence or authorize a different waveform gate. Full Spiral and device-wide 99% accuracy remain unproven.

Fixed onset latency alone does not prove an FFT implementation. [Bernsee's pitch-shifting explanation](https://blogs.zynaptiq.com/bernsee/pitch-shifting-using-the-ft/) describes a phase-vocoder candidate, while [Pioneer's earlier pitch-control patent](https://patents.google.com/patent/US5369725A/en) describes circular-buffer reading and weighted transitions between read positions. These are primary-source algorithm references for experiments, not evidence of RMX-1000 architecture. Neither implementation has been imported into the project. A candidate must explain the measured nonlinear and stereo behavior before full-effect matching can be claimed.

Factory one-shot drum outputs have also been captured locally for analysis; the distributed synthesized substitutes have not yet been matched or replaced. Manufacturer audio remains outside Git.

## Reverb identification: 27 October 2026

The [Reverb record](measurements/2026-10-27-reverb-identification.json) contains 88 verified original 2.2.0 captures at factory settings, 48 kHz and 120 BPM: 56 initial fixtures, 16 prospective timing checks, four long tails and 12 output-filter holdouts. Inputs and controls are generated by [tools.rmx_reverb_characterize](../../tools/rmx_reverb_characterize.py). All numerical analysis runs in the locked uv environment with NumPy and no SciPy. Raw original audio and binaries remain in ignored local artifacts.

Both directions repeat bit-exactly after a fresh instance. A 512-frame input shift gives an exact corresponding output shift in the checked overlap. Scaling a left impulse from 0.002 through 0.02 to 0.2 leaves amplitude-normalized residuals within about 0.00015% RMS. Same-sign and opposite-sign stereo impulse sums agree with separately captured channel responses within about 0.00013% in the checked tails. These support linear, time-invariant identification at the fixed initial controls and tested levels; they do not establish behavior under moving controls or overload.

Main changes reflection timing, rather than only output amount. With a left impulse and Sub1 raw128/Sub2 zero, Up's first detectable left residual moves from 2,208 frames at Main32 to 309 at Main255. Down moves from 502 to 2,146 frames. A quartic Up timing fit and quadratic Down fit, made from the initial captures, predict 16 fresh Main positions within 1.37 frames on both output channels. The declared prediction limit was two frames and the forecasts were saved before capture. This identifies an empirical onset map, not a complete time-warp law, delay network or pitch algorithm. Down's instantaneous input coefficient also falls above the center while Up's remains unity in the checked impulse fixtures.

Sub1 controls decay and does not mute the effect at zero. At Main128/Sub2 zero, the broadband -5 to -35 dB decay extrapolations are:

| Sub1 raw | Up estimated T60 | Down estimated T60 | Capture extent |
| --- | --- | --- | --- |
| 0 | 1.00 s | 1.00 s | 18-second post-input tail |
| 128 | 6.73 s | 6.98 s | 18-second post-input tail |
| 192 | 20.21 s | 21.67 s | 90-second post-input tail |
| 255 | 45.53 s | 49.98 s | 90-second post-input tail |

These are finite-window Schroeder fits with their ranges, fit quality and final-window energy retained. Short recordings bias the longest tails: the initial Down255 fit gives about 37.61 s instead of the long capture's 49.98 s. A single broadband slope does not establish frequency-dependent damping or an exact Sub1 law.

Sub2 is consistent with a separate Butterworth second-order output filter, plus level compensation. The identified fixed model uses `u = max(0, raw - 4) / 251`, gain `1 + 0.5 * raw / 255`, Up high-pass cutoff `54 * (6310 / 54)^u` Hz, and Down low-pass cutoff `17330 * (261 / 17330)^u` Hz. The endpoint frequencies are rounded empirical hypotheses and Q is fixed at `1/sqrt(2)`.

The filter model was saved before 12 fresh captures at withheld knob positions, including independent stereo broadband fixtures. The original neutral-filter reverb supplies the component input. All wet and post-input-tail per-channel comparisons pass the one-percent RMS screen without a comparison gain fit or wet alignment search. Worst wet error is about 0.0017%; worst tail error is about 0.0011%. This identifies the output-filter component only. It cannot certify a clone reverberator because its input still comes from the original.

The [production baseline](measurements/2026-10-27-reverb-production-baseline-48k.json) makes the remaining mismatch explicit: all 52 active, non-silent complete renders fail the declared whole-output/tail screen. Only the two Main-zero and two silence fixtures pass. Production DSP is unchanged. The next task is to recover the delay/diffusion/feedback structure and Main/Sub1 parameter laws, then validate complete independent program material without supplying original-derived wet fixtures. Control gestures, other profiles/rates, listening and physical hardware remain separate requirements.

## Reverb Down autonomous network checkpoint: 27 October 2026

The subsequent [network identification](measurements/2026-10-27-reverb-down-network-identification.json) advances Down at Main128/Sub1-128 from an output-filter component to an autonomous research renderer. Its candidate uses five cross-coupled stereo comb pairs. The observed integer delay pairs are `(1033,1148)`, `(1061,1859)`, `(1147,1964)`, `(1919,1117)` and `(1995,1192)` frames. Each pair's cross-channel first arrival equals the sum of its two delays. Independent left/right impulses identify a unique pairing; later repeats support the same periods.

Two serial allpasses per output use gain 0.7 and delays 335/1091 frames on the left and 395/1031 on the right. A fixed linear filter candidate combines first-order HP80/LP10000 with Butterworth HP54/LP17330. Sub2 changes the latter low-pass and level using the separately validated map. Filter ordering can commute in these static fixtures, so this does not establish the manufacturer's physical ordering or behavior during control movement. Ten feedback gains and one overall wet gain are fitted from the left-input recording after identifying delays with both input channels. Rounded filter frequencies and the topology remain empirical hypotheses, without manufacturer implementation attribution.

[tools.rmx_reverb_network](../../tools/rmx_reverb_network.py) reproduces arrival detection, unique stereo pairing, numerical fitting and a new calibration header using NumPy alone. [reverb_down_neutral_probe.cpp](experiments/reverb_down_neutral_probe.cpp) then processes arbitrary input through its own delays, feedback, filters and diffusers. It supplies no original-derived wet stream. The candidate remains outside the production DSP because Main/Sub1 maps and the wider effect scope are unfinished.

All [28 complete renders](measurements/2026-10-27-reverb-down-network-prototype-48k.json) pass separate whole, wet and post-input-tail per-channel one-percent RMS screens. They include calibration/repeat fixtures and eight new prospective captures after the model was frozen. The fresh cases use independent stereo noise, tones and percussive material, offset stereo impulses, and Sub2 raw0/77/173/241. Worst wet error is about 0.0047%; worst tail error is about 0.0056%. Only the independently reviewed bypass offset is applied, with no comparison gain fit or wet alignment search. Silent controls carry no similarity percentage.

The same fitting/validation commands run in a clean locked uv environment without SciPy. The C++ translation unit compiles with warnings enabled and passes two fresh cases under AddressSanitizer/UndefinedBehaviorSanitizer; sanitized and optimized WAVs are bit-identical. The linked WAV library was not rebuilt with sanitizers. Twelve input, model-binding, calibration, numeric/rate and report/output-preservation guards reject invalid requests. Production code and its earlier failed baseline remain unchanged.

The record also freezes an unvalidated next-step hypothesis: nominal Sub1 decay `1 + 49 * (max(0, raw - 3) / 252)^3` seconds, with feedback gains scaled by the ratio of nominal decay times. Current broadband estimates are consistent with this candidate, but coefficient scaling and wet-level compensation still need identification. Exact Main delay/gain arithmetic, its integer boundaries, Main/Sub1 interaction, Reverb Up, User profiles, gestures, startup, other rates, listening and hardware remain requirements of the full sound-matching goal.

## Reverb Down static control maps: 27 October 2026

Four 256-position sweeps now cover Main at Sub1-128/255 and Sub1 at Main128/255. The [first 512 captures](measurements/2026-10-27-reverb-down-control-identification.json) and [512 interaction captures](measurements/2026-10-27-reverb-down-control-interaction-identification.json) verify exact samples, controls, extents and reference hashes. Main raw0–3 produces no wet output in the checked static fixtures. The saved nominal-decay hypothesis passes all 764 assessable feedback-coefficient predictions across the three applicable sweeps, with maximum absolute gain error about 4.02e-7 against a predeclared 2e-6 limit. These are identification checks, separate from waveform acceptance.

A quadratic describes the smooth nominal Main delay curve closely, but its integer rounding misses one of 2,440 taps excluded from the fit. At Main143, one left delay is 1,171 frames rather than the predicted 1,172. The candidate retains measured integer delays for every active raw Main position. A negative-control renderer with only that tap changed by one frame fails the fresh Main143 fixtures, reaching about 48%/62% wet-channel RMS error for broadband/impulse input. This supports retaining exact timing rather than treating the smooth fit as sufficient.

The first extension multiplied independent Main and Sub1 wet-level maps. All 564 sweep/prior renders passed, but 14 of 64 fresh mixed-control cases failed. Those failures remain in the [rejected separable report](measurements/2026-10-27-reverb-down-control-separable-prototype-48k.json), with the source checkpoint preserved at `9364cfd`. A diagnostic gain fit reduced their residuals below about 0.005%; it was not used for acceptance. This isolated a wet-level interaction while preserving the feedback model.

The two added sweeps identify a rank-two level model. Let `Gm` and `Ga` be the first two level maps, and `Cm`/`Ca` the corrections identified from the additional sweeps. The fixed candidate uses:

```text
wet_gain(Main, Sub1) = Gm[Main] * Ga[Sub1] / Ga[128]
                      * (1 + Cm[Main] * Ca[Sub1])
```

The [frozen interaction model](measurements/2026-10-27-reverb-down-control-interaction-model.json) was then tested on 64 new captures with different signals, control combinations and Sub2 positions, including inactive controls, the dry crossover, Main143 and long tails. All [1,204 complete renders](measurements/2026-10-27-reverb-down-control-interaction-prototype-48k.json) pass separate whole/wet/post-input-tail per-channel one-percent RMS screens: 1,024 calibration captures, 64 earlier mixed-development cases, 64 fresh prospective mixed cases and 52 prior fixtures. Worst wet/tail errors are about 0.0058%/0.0060%. All earlier 628 cases now pass, fixing the 14 failures without losing a previous pass. No comparison gain or wet alignment is fitted.

The NumPy-only tools and generated [control calibration](experiments/ReverbDownControlCalibration.h) reproduce this static raw-control candidate. The renderer's legacy neutral invocation remains bit-identical on all 28 earlier cases. Warnings-enabled builds, two sanitizer renders, 14 invalid-input/provenance guards and the one-frame negative control pass their stated checks; the linked WAV library was not rebuilt with sanitizers. Production DSP is unchanged. Fractional controls, moving/activating/bypassing effects, other profiles/rates/tempos, overload, Up, listening and hardware remain outside this checkpoint and are still part of the full sound-matching goal.

This is a measured static software milestone. It does not establish full-device 99% similarity, hardware equivalence, overload behavior, host-rate conversion, modulation/resonance/reverb matching, sampler/Release matching, control-transition accuracy or listening equivalence. Those remain the next stages of the same measurement campaign.

## Reverb Down moving controls: 27 October 2026

The [state/timing investigation](measurements/2026-10-27-reverb-down-motion-characterization.json) adds 61 verified original captures: 12 button cases, 31 static-baseline/step cases, 12 baseline/ramp cases and six host-block repeats. Sources include independent stereo noise/tones, a two-second input gap and spaced channel impulses. All six block repeats are bit-identical to their corresponding original renders at block sizes 32, 128 and 256.

Turning the button off during the input gap preserves the existing tail exactly in the checked window. With continuous input, the change begins at the next 32-frame input boundary: the dry contribution changes there, and the first wet difference follows the shortest comb delay. Main/Sub1/Sub2 changes first affect raw output at that boundary instead; relative to the independently measured 32-frame bypass latency they occur one internal block earlier. These observations distinguish button/input and knob/output timing. They are measured timing relationships, not permission to fit wet alignment.

The [first stateful research candidate](measurements/2026-10-27-reverb-down-motion-first-prototype-48k.json) retains delay/filter state and updates controls every 32 frames. It passes 26/61 complete comparisons: all 24 static baselines and two initially disabled impulse cases. Every moving-knob case and the remaining button cases fail the unchanged one-percent whole/wet/tail/event-window gates. The failures show why the 1,204 static passes cannot establish moving-control accuracy. Candidate-predicted dry subtraction is diagnostic and does not establish independent wet-component fidelity.

Motion tools bind exact source samples, controls/events, host blocks, duration and receipt hashes. Full raw captures stay under ignored build artifacts; numeric findings and failed comparisons are retained here. Production remains unchanged. Input/send gain placement, filter-state realization, variable-delay pointer behavior and the two timing paths need identification and fresh dynamic holdouts before integration.

The [next stateful checkpoint](reverb-down-motion.md) identifies Sub2 moving one raw step per 32 samples. With separate causal input/output timing and persistent filter state, the [current matrix](measurements/2026-10-27-reverb-down-motion-slew-prototype-48k.json) passes 42/69 renders: 34/61 earlier cases and all eight new prospective cutoff-motion cases. All 16 cutoff-only motion cases pass every whole/wet/tail/event-window gate. The fresh worst wet event window is 0.9928%, close to the 1% limit. The [audit](measurements/2026-10-27-reverb-down-motion-audit.json) verifies parameter readbacks, independent bypass timing, seven provenance guards and two sanitizer renders. Twenty-seven button/Main/Sub1/combined failures remain; production is unchanged.
