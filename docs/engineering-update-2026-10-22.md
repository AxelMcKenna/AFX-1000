# Engineering update, 22 October 2026

## Implemented

- AUTO pulse-phase estimation and gradual clock correction, silence invalidation and tempo-change recovery. This estimates a beat pulse, not the musical start of a bar.
- Shared MIDI clock receiver with Start/Stop/Continue, Song Position Pointer, batched timestamps and native running-status parsing. Plugin MIDI clock/transport processing splits at sample offsets while keeping DAW transport priority.
- Independent loop tempo and pitch using bounded, stereo-linked overlap-add and waveform alignment. Neutral playback retains direct interpolation. No callback buffers or dependency were added; 32 voices add 1 KiB of state.
- An isolated optional Ableton Link adapter and native setup control. Normal builds keep it disabled and do not fetch the SDK or open Link sockets.
- Original generated panel artwork in native and plugin builds. The previous hardware photograph is removed from current source/products.
- Reference probe/capture/comparison tooling, a persistent-engine offline stress tool, a plugin smoke host, and package/source/dependency archives with hashes and actual dependency notices.

## Verified source snapshot

Other work was modifying this workspace concurrently. The final build and test results below refer to a captured source snapshot; package manifests record its exact source hashes. Subsequent workspace changes are not automatically covered by these results.

| Check | Result |
| --- | --- |
| Universal native, AU, VST3 and JUCE standalone builds | Built for arm64 and x86_64, macOS 12 deployment target |
| Integrated Release CTest | 14/14 passed, 4.59 seconds |
| Fresh ASan/UBSan build and CTest | 14/14 passed, 10.14 seconds; no sanitizer diagnostics |
| VST3 runtime smoke host | 329 checks passed; 138 project parameters; 4624 processed blocks |
| VST3 endpoint/mode/state/MIDI/rate tests | Neutral stereo, all project endpoints, Scene/Isolate modes, state recall, four pad notes and 28 rate/block/transport combinations passed |
| JUCE host plumbing | 2080 MIDI-forwarding parameters and 1 wrapper bypass explicitly classified, separate from project controls |
| Scene/Isolate Release benchmark | Worst p99 1.74218% of the 48 kHz/128-frame deadline on this Mac |
| Persistent offline stress | 7200 simulated seconds at 48 kHz, 345600000 frames, 1305276 callbacks, 39.3662 wall seconds |
| Offline stress signal/event integrity | No non-finite output or dropped events; peak 1.25 in the engine's intentional soft-protection region |
| Offline timing diagnostics | 3 callbacks exceeded their frame deadline; p99 deadline fraction upper bound 0.015 |
| Firmware cross-build and ELF placement | Passed with the snapshot's current DSP/headers; 205,704 QSPI bytes, 47,640 AXI SRAM bytes, 18,204 DMA-region bytes and the 60 MiB SDRAM arena |
| Source ZIP checks | Fixed timestamps, hashes, permissions and exclusions pass |

The accelerated stress run includes blocks from 1 to 1024 frames and ran alongside other development work. It is not a physical two-hour audio session, device underrun measurement, GUI soak or leak measurement. Output above unity may require attenuation before a DAC or integer export. No analog SNR, THD or headroom achievement is established.

## Still open

- No real RMX reference recordings or loudness-matched listening comparison. DSP control roles and synthetic checks do not establish sonic parity.
- Real music, mixed-track AUTO behavior, FLX4/FLX6 routing/cue separation, actual Mac device recovery and a real two-hour session remain unverified.
- VST3 smoke-host success is not certification in a real DAW and excludes editors/dialogs, timer behavior, user-sample project recall and controller feedback.
- AU builds, but its runtime probe could not register the explicit component in this execution environment: `Process-local AudioComponentRegister returned null; visible_system_components=0; matching_before=0; matching_after=0; component_flags=0; factory_symbol_resolved=true; public API supplies no OSStatus`. That failure does not establish its cause. AU runtime remains unverified.
- Link-enabled compilation and live peers were not tested because the separately supplied SDK was unavailable. The SDK-free adapter build does not close that gap.
- Firmware has not been flashed. Codec, SDRAM/cache, SD, control wiring, watchdog/bypass, callback deadlines and analog carrier measurements require the physical board.
- A project source license is awaiting the owner's choice. Dependency terms remain separate.

See [synchronization](synchronization.md), [sample stretching](sample-stretching.md), [reference/runtime validation](reference-validation.md) and [Mac packaging](release.md).
