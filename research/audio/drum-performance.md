# Drum profiles and performance timing

30 October 2026. This campaign uses the locally installed **RMX-1000 Plug-in 2.2.0** as the reference. The actual production Engine now passes **504 reference programs** for custom drum synthesis and Default drum performance at stereo48k. Optimized and AddressSanitizer/UndefinedBehaviorSanitizer renders have identical complete WAV bytes. These are fixed-alignment waveform checks, not a whole-device perceptual similarity percentage. The float fixtures and plug-ins preserve above-unity reference peaks; the native app retains its existing output-protection policy.

| Qualified native scope | Complete programs | Boundaries |
| --- | ---: | --- |
| Gain, decay and envelope for all four drums | 296 | All168 gain/decay/envelope combinations, plus128 fresh pitch/level/retrigger programs; User mode, default pitch ranges, effects off |
| Hold and Quantize | 128 | Discovery, corrected regressions, independent fresh programs and initial-Hold/touch/reselection edges; Default, manual120BPM |
| Auto-tempo rolls | 32 | 91/137/160/187BPM discovery and103/129/151/179BPM fresh tests; external PPQ, fragmented callbacks |
| Overdub, mute and delete | 48 | Free/quantized recording, stopping recording, muting/unmuting and deleting one drum's pattern; Default/manual120BPM |

The [validation receipt](measurements/2026-10-30-drum-performance-validation.json) records the source/binary hashes, full reports, independent arithmetic, negative controls, delivery checks and local archive. Earlier [drum synthesis, gestures and drum/FX routing](drums.md) remain separate evidence. A passing relative RMS error limit of1% in a declared window does not mean99% perceptual similarity across a device.

## Accessing the User settings in the original plug-in

The original exposes52 performance parameters, but its drum customization is stored in the native state. Read-only inspection identified a bounded customization schema. The public host's existing native-state loader was sufficient; no original plug-in code, DSP state or captured audio was modified.

[`rmx_drum_user_settings.py`](../../tools/rmx_drum_user_settings.py) validates the state extent and its `para`, `sett` and `cstm` chunks. The customization chunk has three length-prefixed UTF-8 strings: the RSD file path, its directory and its XML. The script generates a small drum-only RSD file, places its path and contents into a copy of a captured default state, then restores it through the original's public state API. It explicitly selects User mode and verifies that the saved initial state retains exactly the requested customization bytes. The state, XML, plan, readbacks, receipts and all hashes remain in the private local evidence archive.

Two setup failures were retained. XML without its declaration was not accepted by the original's parser. Supplying inline XML with an empty file path parsed, but serialization dropped the customization because the original re-read the named RSD file. Giving it a real generated file solved the round trip. These failed loader attempts are not sound-match results.

This made it possible to exercise every combination of seven gain choices, three decay choices and two envelope choices for kick, snare, clap and hi-hat. Sparse scalar observations informed independent generators; the complete original renders decided whether the reconstruction passed. The production implementation reproduces the different tone/noise/tail decay laws, envelope shapes and per-drum gain placement, including the hi-hat's profile-dependent compensation. No reference recording is embedded in the synthesizer.

## Hold and Quantize

The clock distinguishes physical touch, a touch retained by Hold, strip assignment and instrument selection. Hold can start a silent clock before a drum has been selected. Selecting a drum while that clock is running must not invent an immediate hit. Releasing the physical strip while Hold is engaged preserves the roll; turning Hold off while still physically touching must preserve the physical touch. A repeated strip-position write can rearm a previously released assignment.

Quantize uses a quarter-beat grid with a measured early acceptance interval of0.0325 beats. A narrower initial hypothesis passed discovery but failed four first fresh predictions. Those failures remain failed; correcting the interval made them regressions. A second independent32-program set passed with frozen audio predictions. Wider initial-Hold and touch-order cases then exposed initialization ordering: the factory source's initial stop cue must be consumed before the new Hold state.

[`FactoryRollClock.h`](../../include/rmx/FactoryRollClock.h), the Engine's existing sample-offset cue stream and [`ControlSurface.h`](../../include/rmx/ControlSurface.h) implement these behaviours. The cue remains28 bytes, so the change adds no audio-buffer allocation.

## The Auto clock's callback correction

A naive BPM-only clock failed all16 initial Auto programs. The original derives its block increment from the difference between successive host PPQ positions divided by the **current** callback length. Parameter events fragment callbacks, so a short callback can change this increment. The original rejects implausible increments and carries a pending backward correction until it has drained; a sufficiently large correction freezes a generated32-frame tick. Starting a roll at that boundary also preserves phase history that affects the next retrigger.

A pinned, read-only debugger observer sampled only clock scalars. An independent replay reproduced all67 sampled timeline/increment/correction states exactly. The observed and normal reference renders had identical audio, saved states, plan, parameter log and final inventory. The earlier57/67 replay and intermediate6/16 audio result remain in the archive. Scalar agreement was used to explain the model, then complete audio and unseen programs validated it.

This is scoped to the supplied PPQ programs and callbacks. It does not qualify arbitrary seeks, tempo ramps, audio-derived BPM detection or every stop/resume transition.

## Overdub stores musical commands

The original records a128-slot, four-beat command pattern rather than replaying rendered drum audio. Free recording uses1/32-beat slots; Quantize uses a quarter-beat grid. The pattern origin is snapped, and newly written commands that lie just ahead of the write position must be suppressed on their first read. Otherwise a physical hit can be followed immediately by an unintended duplicate.

The first reconstruction failed all16 programs. Correcting the grid, write suppression and playback state closed the original set. The first unseen set still rejected four predictions near the loop boundary: a rounded slot128 wraps to slot0 and must receive the same suppression as an upcoming slot. Those four predictions remain rejected. The correction passes them as regressions and passes a second independent16-program set predicted before capture.

Mute continues to synthesize and advance the recorded drum, with a160-sample output fade. This lets unmute reveal the correct ongoing voice. Deleting a pattern or turning recording off lets a sounding drum finish. Unit tests also check that clearing a pattern allows subsequent recording and that these audio paths allocate no memory in the callback.

[`FactoryDrumSequence.h`](../../include/rmx/FactoryDrumSequence.h) uses bounded command/velocity metadata alongside the common generated clock. The existing sequencer remains available for other sources and unsupported profiles. The measured overdub path is deliberately limited to the qualified Default/manual120BPM/internal-drum scope.

## How the comparisons are checked

[`rmx_drum_performance.py`](../../tools/rmx_drum_performance.py) and [`rmx_drum_user_match.py`](../../tools/rmx_drum_user_match.py) run the actual Engine. Fresh campaigns save complete candidate WAVs, source hashes, input hashes, recipes and executable hashes before starting the original captures. Correcting a failed prediction changes its role to regression; the historical prediction is never relabeled.

Before scoring, the tools verify original identity, host and binary files, input samples, exact plans, callback lengths, parameter readbacks, saved state and receipt auxiliary hashes. Both channels are evaluated separately at the fixed32/32 transport offsets, with no gain fitting or alignment search. Every declared whole-output, one-second, event or drum attack/body/decay window must pass. Sanitized and optimized complete WAV containers must be identical, and sanitizer stderr must be empty.

[`rmx_drum_performance_audit.py`](../../tools/rmx_drum_performance_audit.py) independently recomputes every window and rejects silence, polarity inversion, a silent right channel, a32-frame shift and a2% gain error for each program. Failed predictions remain failed even when their arithmetic is independently verified. Complete outputs are retained as WAVs or lossless gzip with a checked decompressed SHA-256. Storage compression changes no sample or gate.

[`rmx_drum_user_plugins.py`](../../tools/rmx_drum_user_plugins.py) checks the64 new User programs through each explicit project AU/VST3 bundle, using MIDI pads and normalized host controls. It checks original windows, native-delivery limits, latency, receipts and parameter readbacks. Native Hold/strip/overdub evidence and wrapper User-drum evidence are distinct; the wrapper does not expose the original's complete strip-control interface.

## Remaining gaps

Custom drum rolls and overdubs, moving customization during a voice, alternate pitch ranges/rates, multiple drums in an overdub pattern, recording strip gestures, tempo changes/seeks, sampling and combinations with active effects need further reference campaigns. This work does not qualify every button, every setting or physical hardware. The inherited near-null mixed-Crush wet-window failure and firmware-host factory-silence failure remain recorded.

Reproduction uses `uv run --locked python -m tools.rmx_drum_performance` (`predict`, `capture`, `compare`) and the corresponding User settings/matching modules. Original captures require the user's local original plug-in and Intel reference host; the project never downloads or redistributes that plug-in. Build the excluded CMake targets `rmx_drum_performance_probe` and `rmx_drum_user_probe` for native fixtures; use an instrumented build for the sanitizer arguments. Every destination must be new.
