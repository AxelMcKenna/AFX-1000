# Combined drum performance against the original plug-in

30 October 2026. This follow-up qualifies **204 further reference programs** at stereo48k/default pitch ranges:102 discovery programs and102 complete predictions frozen before new original captures. It covers mixed-drum patterns, custom drum profiles during rolls/overdubs, and drums through all nine deterministic Scene effects. Every optimized/sanitized complete WAV pair is identical. All whole-output, one-second and event windows pass the unchanged1%per-channel gates; every active-FX wet window also passes after subtracting its explicitly matched dry program. These are scoped waveform tests, not a whole-device perceptual percentage.

| Native campaign | Discovery | Fresh | What is exercised |
| --- | ---: | ---: | --- |
| Mixed-drum overdubs | 18 | 18 | Simultaneous/staggered notes, replacement, Quantize, two-pad mute/unmute/delete, re-recording, recording-off while muted and dense128-slot/four-drum patterns |
| Custom-profile rolls | 24 | 24 | All four drums, gain/decay/envelope combinations, pitch, Hold, Quantize, repeated strip assignment and reselection |
| Custom-profile overdubs | 24 | 24 | Free/quantized recording, mute/delete, re-recording and paired drums with independently configured profiles |
| Mixed drums and Scene FX | 36 | 36 | Default/User, nine deterministic effects,18 active programs and18 matched dry programs per set; the fresh set also includes rolls or overdubs |

The earlier [504-program drum checkpoint](drum-performance.md) is preserved as a separate record. The [new validation receipt](measurements/2026-10-30-drum-combo-validation.json) links complete numeric reports, failed baselines, independent arithmetic, preservation checks, build evidence and the private local archive.

## Changes identified from the reference

The initial mixed-pattern model passed16/18 programs. Both failures happened when recording was switched off while two drums were muted: the native pattern reset cleared its mute targets and exposed voices that were still sounding. The original preserves those output mute targets after recording stops. The bounded factory sequence now preserves them when disabled. Deleting or replacing pattern commands and the existing voice fade retain their earlier behaviour.

The original also supports drum-only User customization without changing its roll/recording clocks. The engine previously rejected User mode from those measured paths, sending it through its older timing implementation. That baseline passed8/24 custom-roll programs and0/24 custom-overdub programs. The measured paths now admit User drum profiles when the default strip beat assignments and pitch ranges are retained. Custom strip assignments still use their existing fallback; they are not qualified by this campaign.

Correctly configured initial FX tests passed34/36 programs. The two failures were User-mode Spiral Up/Down. Their sound settings were still at factory defaults, but a blanket User-mode guard selected the older processor. The dispatch now checks the actual Scene settings, so changing drum profiles can use the identified Spiral processor while unsupported Scene customization retains its fallback. The fresh FX set validates the composition with rolls and overdubs as well as static drum profiles.

One FX setup attempt omitted the three Scene knob parameters, leaving the original at its initial knob values. That attempt and its comparison error are retained as rejected setup evidence. It was recaptured under a new session with explicit knob delivery. It is not counted as a valid sound-match baseline or a fresh prediction.

## Host normalization caught by wrapper tests

The first AU and VST3 delivery runs each passed32/36 programs. User-mode Spiral and reverb failed even though their native Engine programs passed. A JUCE8.0.6 range diagnostic reproduced the cause: the native reverb-decay default is `0.720000028610229`, while its normalized round trip decodes to `0.719999969005585`. That prevents exact factory-profile recognition in User mode. The diagnostic also records the Scene-time default and the previously handled unity-gain round trips.

The wrapper now caches each parameter's exact normalized-default representation and maps that one value back to the declared native initial value. It uses exact equality, with no tolerance band around neighbouring automation values. Both formats then pass all36 sound programs and359 runtime checks each. The failed deliveries, their binaries, the scalar diagnostic and corrected deliveries remain separate evidence.

## Reference and prediction protocol

[`rmx_drum_combos.py`](../../tools/rmx_drum_combos.py) builds repeatable programs through the actual production Engine. Version2 of the [native fixture](../../tools/drum_performance_probe.cpp) adds static drum profiles and Scene controls while retaining the version1 interface used by the earlier programs. The reference uses the existing public RSD/native-state loader: each requested User customization must survive the original's saved-state round trip.

The fresh programs change callback lengths, event phase, level, pitch and all four drum profiles. Complete candidate WAVs, the executable, source files and their hashes are frozen before original captures. The matched dry/active programs share identical source controls and events. Wet subtraction uses those declared partners; there is no gain fitting, time search or reference-derived correction.

Comparisons verify exact plans, control readbacks, input extent, receipts, auxiliary files, state retention and pinned original/host binaries. Both channels must pass at fixed32/32 transport offsets. Optimized and ASAN/UBSAN complete output and dry WAV bytes must agree, with empty sanitizer stderr. The [independent auditor](../../tools/rmx_drum_performance_audit.py) separately recomputes every full and wet window and rejects five whole-output negative controls for every program.

[`rmx_drum_combo_compat.py`](../../tools/rmx_drum_combo_compat.py) replays the preceding504 programs through the current Engine and sanitizer builds. It requires complete WAV/dry-trace byte identity with the qualified parent, rechecks original provenance and retains the results losslessly. This transfers the earlier window results without changing their gates or calling old programs new holdouts.

The excluded CMake target `rmx_drum_performance_probe` accepts both fixture versions. To reproduce a new campaign, run `uv run --locked python -m tools.rmx_drum_combos predict`, `capture` and `compare` with a fresh stage, new destinations, explicit local original/reference host and the sanitizer fixture. Discovery stages omit `-fresh`; qualifying a correction against a previously captured fresh stage requires `--regression`. The original binary, native chunks, audio and private observations are never committed to Git.

## Delivery and limits

The app, AU and VST3 use the same production core. AU/VST3 delivery checks use the36 mixed one-shot/dry/active-FX programs, including User profiles and all nine deterministic Scene effects, and independently check every native whole/wet window. Separate native-delivery limits and reported latency32 are required. Native strip/mute/delete event coverage is separate from wrapper MIDI/parameter coverage; the wrapper does not expose the original's full strip/button interface.

The engine object and prepared audio-buffer budget remain unchanged. The native app keeps its existing output-protection policy; floating-point comparisons and plug-in delivery preserve above-unity reference peaks.

Noise statistics, arbitrary custom Scene/Isolator settings, nondefault strip assignments, other pitch ranges/rates, tempo ramps/seeks, recording strip gestures and physical-board/controller behaviour remain unqualified. The earlier near-null mixed-Crush wet-window failure and firmware-host factory-silence failure remain documented; this campaign does not relabel or erase them.

The subsequent [recorded-strip/division/transport campaign](drum-gestures.md) extends this checkpoint. Its240 programs and the earlier708 now have a bounded948-program current-engine byte replay; raw renders are deleted after each case. [User Noise widths](noise-user.md) are qualified separately through statistical screens.
