# Validation record

Verified during development on Apple Silicon macOS 26.6.2:

- Native macOS application builds, opens, enumerates audio/MIDI devices, and starts output.
- Direct rekordbox process capture and Mac speaker output started at 44.1 kHz; the user confirmed audio and effects were working.
- JUCE 8.0.6 standalone, AU, and VST3 artifacts compile and link locally. This is not DAW certification.
- Universal native app, AU, and VST3 builds contain both arm64 and x86-64 slices. The native app's minimum binary deployment target is macOS 12.0; application capture requires 14.2+. Intel runtime testing remains outstanding.
- Engine tests cover neutral stereo, wet-only null, all ten Scene FX producing a changed output, the four isolator modes at 44.1/48/88.2/96 kHz, release resets, sampler playback, invalid values, state round trips, WAV, event queue behavior, all shared panel actions, and Scene FX hit areas.
- Synthetic pulse tests at 90/120/128/150/173 BPM lock within 2.5 BPM; observed errors were below 1 BPM. Performance on arbitrary music and tempo changes needs listening and additional fixtures.
- Allocation tracking found no allocations during variable-size audio processing with input roll and band rolls active.
- Live UI automation exercised all 10 Scene FX choices, four isolator modes, four pads, mode/source toggles, Default/User, all exposed sliders, release selection/lever, tap, and nudge. Read-back values confirmed the changes. Audio was stopped during this UI sweep; signal behavior is covered separately by engine tests.
- A development benchmark before the final control audit reported worst p99 around 1.8% of the 48 kHz/128-frame deadline. Run `rmx_benchmark` for the current code and machine.

Outstanding: physical FLX4/FLX6 routing and headphone separation, a live two-hour soak, loopback latency/noise/distortion measurements, DAW-host automation/validation, Intel Mac runtime checks, ARM Linux runtime performance, and reference-unit sonic comparisons.

## Performance changes, 23 October 2026

Local Release validation passed 30 CTests, including concurrent plugin imports, bounded asset retention with playback stopped, no callback allocation/deletion, snapshot ownership, negotiated buffering and DSP state transitions. The headless ASan/UBSan suite passed 27 tests; TSan with the native controller passed 28. Additional ASan/UBSan and TSan runs instrumented the real processor, core and asset regression while reusing the existing JUCE/AppKit libraries without instrumentation.

A deterministic before/after rendering compared 921,600 output samples across 44.1/48/96 kHz, scenes, isolator modes, rolls and release transitions: all samples were byte-identical. Separate regressions cover a roll frozen on silence, crossover cache invalidation after rate changes, audible reverb tails and waking after decay. Reverb residue below 1e-15 is flushed incrementally; no delay-buffer clearing happens inside processing. Disabled reverb stops accepting new input after its fade, and Auto BPM starts a fresh analysis window when enabled.

Replacing the same 30-second, 48 kHz stereo sample 16 times without processing previously grew live C++ allocations from approximately 33 MiB to 243 MiB. The same reproduction now remained at approximately 44 MiB after imports 1, 4, 8 and 16. The asset exchange retains at most two bank snapshots after publication, with a third slot used during transfer. Unchanged sample payloads are shared, and reclamation occurs on the publisher.

Median mean processing times from three paired 5,000-block runs at 48 kHz/128 frames:

| Workload | Before | After | Reduction |
| --- | ---: | ---: | ---: |
| Neutral | 8.11 µs | 5.23 µs | 36% |
| Drive | 11.86 µs | 6.68 µs | 44% |
| Reverb Up | 7.99 µs | 7.01 µs | 12% |
| Automation | 8.40 µs | 7.49 µs | 11% |
| Combined effects, voices and capture | 22.64 µs | 21.41 µs | 5% |

The expanded 25-workload matrix passed its p99 < 50% gate across 225 configurations with 2,000 measured callbacks each. Its worst p99 was 18.94% of deadline. It also recorded 15 wall-time overruns, with a maximum of 554.72% of deadline; these ordinary offline runs include OS scheduling and do not establish live callback compliance. The benchmark reports those overruns and offers `--strict-max` to reject any of them. CI stores the full CSV per platform.

Both firmware profiles cross-compiled after the changes and all nine firmware host suites passed. The 48 kHz engine buffer payload remains 26,433,392 bytes, with zero processing allocations in the measured workload. These checks do not establish MCU execution time, physical round-trip latency or the real-device underrun/latency tradeoff.

A subsequent direct-capture restart timed out in desktop automation, followed by automation failures on other applications. Audio initialization now runs on a separate control queue and reports progress so a slow system call cannot block the interface. The new live restart path still needs verification; the automation failure does not establish its cause.

Do not describe this build as a certified hardware emulation or as fully qualified for live sets based only on the synthetic checks.
