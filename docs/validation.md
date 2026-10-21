# Validation record

Verified during development on Apple Silicon macOS 26.6.2:

- Native macOS application builds, opens, enumerates audio/MIDI devices, and starts output.
- Direct rekordbox process capture and Mac speaker output started at 44.1 kHz; the user confirmed audio and effects were working.
- JUCE 8.0.6 standalone, AU, and VST3 artifacts compile and link locally. This is not DAW certification.
- Engine tests cover neutral stereo, wet-only null, all ten Scene FX producing a changed output, the four isolator modes at 44.1/48/88.2/96 kHz, release resets, sampler playback, invalid values, state round trips, WAV, event queue behavior, all shared panel actions, and Scene FX hit areas.
- Synthetic pulse tests at 90/120/128/150/173 BPM lock within 2.5 BPM; observed errors were below 1 BPM. Performance on arbitrary music and tempo changes needs listening and additional fixtures.
- Allocation tracking found no allocations during variable-size audio processing with input roll and band rolls active.
- Live UI automation exercised all 10 Scene FX choices, four isolator modes, four pads, mode/source toggles, Default/User, all exposed sliders, release selection/lever, tap, and nudge. Read-back values confirmed the changes. Audio was stopped during this UI sweep; signal behavior is covered separately by engine tests.
- A development benchmark before the final control audit reported worst p99 around 1.8% of the 48 kHz/128-frame deadline. Run `rmx_benchmark` for the current code and machine.

Outstanding: physical FLX4/FLX6 routing and headphone separation, a live two-hour soak, loopback latency/noise/distortion measurements, DAW-host automation/validation, Intel Mac runtime checks, ARM Linux runtime performance, and reference-unit sonic comparisons.

A subsequent direct-capture restart timed out in desktop automation. Earlier direct capture worked and was confirmed by the user, but repeated restart reliability remains under investigation.

Do not describe this build as a certified hardware emulation or as fully qualified for live sets based only on the synthetic checks.
