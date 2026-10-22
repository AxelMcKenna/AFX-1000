# Synchronization

## Clock priority

The native Mac adapter follows an enabled Ableton Link session with at least one peer, then a selected MIDI source with valid transport, then the engine's AUTO or manual clock. Plugin-host transport retains priority in the plugin adapter.

AUTO estimates the input pulse. It cannot infer which quarter note is the start of a bar. A mixed rekordbox master may contain two different tempi during a transition. TAP, manual BPM, MIDI clock or a host grid remain useful when the rhythm is ambiguous.

## AUTO changes

- Separate stereo channel energy prevents cancellation of an anti-phase kick.
- Centered onset correlation rejects a steady novelty baseline.
- The rolling evidence window is four seconds. One lag is evaluated every approximately 5 ms. At the end of a lag sweep, up to four competing octave correlations are rechecked against the same window, followed by a phase estimate. Every scan has at most 800 entries.
- Quarter-note phase comes from the circular mean of recent onset positions at the selected tempo.
- `phaseSlew(beat)` returns a bounded correction of at most 0.25 beats per second. The engine uses it with AUTO and QUANTIZE to align a continuously advancing clock without assigning a new beat position or firing duplicate sequence steps.
- Confidence falls when onsets disappear. Sustained silence clears lock and preceding-track evidence within 0.75 seconds after the detector envelope falls below its silence threshold.
- A large tempo change replaces the preceding tempo instead of slowly averaging between unrelated tracks.

Confidence is an internal consistency measure, not a calibrated probability. Half/double-time ambiguity, syncopation, rubato, sparse breakdowns and two tracks in a DJ mix still need listening and corpus evaluation.

## MIDI changes

`MidiClock.h` is a fixed-storage receiver and byte parser. The native and plugin adapters use it for:

- Start, Continue and Stop. The first timing pulse after Start is beat zero. Stop holds sequence transport stopped while audio processing continues.
- Song Position Pointer in MIDI sixteenth-note units.
- Running-status notes and real-time clock bytes interleaved inside another message.
- Multi-pulse tempo measurement rather than averaging reciprocal single-pulse intervals.
- Batched pulses sharing a timestamp, source changes and clock timeout.

In the plugin, MIDI clock and transport messages split processing at their sample offsets. Host tempo and position keep priority. MIDI CC changes still use block-level handling.

A source's batched timestamps cannot reveal the original spacing of each pulse. Software does not recover information that the sender discarded. Host timestamps also remain dependent on the selected audio device and driver.

## Optional Ableton Link adapter

The adapter targets [Ableton Link 3.1.5](https://github.com/Ableton/link/releases/tag/Link-3.1.5), commit `45931b8bd2a7066f1950f2a0beab81a0c51f28fe`. SDK-free builds compile a disabled adapter and do not open Link sockets. There is no dependency download during a normal build.

Link is [dual licensed by Ableton](https://github.com/Ableton/link/blob/Link-3.1.5/LICENSE.md), under GPLv2-or-later or a proprietary agreement. Enabling this optional component must follow those terms. This dependency is separate from the project's own license.

For an explicitly enabled build, supply a local checkout at the supported tag, including its Asio submodule. Expected files:

```text
AbletonLinkConfig.cmake
include/ableton/Link.hpp
modules/asio-standalone/asio/include/asio.hpp
```

The CMake integration exposes `RMX_ENABLE_LINK` defaulting OFF and `RMX_LINK_PATH`. An enabled native target includes the SDK's CMake config, links `Ableton::Link` and defines `RMX_ENABLE_LINK=1`. It always builds `src/macos/LinkSession.cpp` so SDK-free builds retain the same native interface.

The adapter follows the session's tempo and four-beat phase. It does not publish tempo changes, start/stop commands or audio. It uses the [audio-thread session capture API](https://github.com/Ableton/link/blob/Link-3.1.5/include/ableton/Link.hpp). CoreAudio output host time, with output-device and selected-stream latency, is converted to the Link clock's microsecond domain. Ableton describes timestamp and output-latency requirements in its [integration documentation](https://github.com/Ableton/link#time-and-clocks).

Link-enabled builds and peer discovery were not run in this environment because the SDK and its submodule were not available locally. A disabled adapter build is not proof of working Link synchronization. The [official Link test plan](https://github.com/Ableton/link/blob/Link-3.1.5/TEST-PLAN.md) and loopback timing checks remain required before calling the optional adapter release ready.

## Checks run during this change

`tests/tempo_tests.cpp` was built directly with Clang, first with optimization and warnings, then with AddressSanitizer and UndefinedBehaviorSanitizer. Both runs passed.

| Check | Result |
| --- | --- |
| Synthetic kick + eighth-note hat + sustained tone, anti-phase stereo | All 15 combinations passed at 44.1, 48 and 96 kHz, for 90, 120, 128, 150 and 173 BPM |
| BPM error after 14 seconds | Less than 1 BPM in those fixtures |
| Quarter-note phase error after 14 seconds | 0.003 to 0.039 beats in those fixtures |
| Silence after a locked rhythm | Lock cleared after one second of zero samples |
| New 150 BPM rhythm following silence | Reacquired within seven seconds |
| Direct 150 to 90 BPM transition | Reacquired within seven seconds |
| Plain 173 BPM kick, four onset offsets | No half-time lock after 14 seconds |
| Additional plain-kick range diagnostic | 56 combinations from 70 to 179 BPM and four onset offsets passed |
| Sustained 220 Hz tone | No retained rhythmic lock |
| NaN/infinite input and invalid preparation rate | Finite BPM and no lock |
| MIDI 128 BPM with timestamp jitter | Tempo within 1 BPM; first Start pulse synchronized at beat zero |
| MIDI groups of four equal-timestamp clocks | 120 BPM estimate retained |
| MIDI Stop, Song Position Pointer, timeout and reset | Passed |
| Real-time interleaving and note running status | Passed |
| Native `AudioHost.mm` translation unit | Compiled successfully with the disabled Link adapter |
| SDK-free `LinkSession.cpp` translation unit | Compiled successfully |

These are deterministic engineering fixtures. They are not a commercial-music benchmark, a rekordbox live test, a physical controller test or a claim of RMX-1000 beat-detection parity.
