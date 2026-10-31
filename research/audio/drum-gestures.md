# Recorded strips, beat assignments and host transport

30 October 2026. The original RMX-1000 Plug-in 2.2.0 now has **240 further scoped drum performance programs** passing the unchanged per-channel audio gates: 96 recorded-strip programs, 96 custom-division programs and 48 host-transport programs. These are stereo48k software-reference tests, not a whole-device accuracy percentage.

Each family has discovery, first fresh and second fresh sets. The final model's second fresh set contains80 complete predictions frozen before Original captures. Two failures in the first fresh set were corrected and remain failed predictions in the historical evidence; replaying those programs successfully is regression evidence. The independent audit recomputed all240 programs and rejected five whole-output negative controls per program.

The [current bounded replay](measurements/2026-10-30-gesture-noise-drums948.json) transfers these240 and the preceding708 drum/performance programs to the delivered engine through complete optimized/ASAN audio and dry-WAV byte identity. The Original WAVs were removed during the requested cleanup. This replay checks retained schedules, receipts, prior results and candidate digests; it does not claim to reread deleted reference audio. Earlier complete comparisons and their numeric audit are retained in the cleanup metadata archive.

## What changed

The Original records a touched strip as a sequence of commands, rather than recording each resulting drum hit. The engine now stores bounded strip commands alongside its128 musical pattern slots. Its strip writer leads the reader by one grid cell, accepts one write per recording cell, and preserves the selection/phase information used to generate repeats on playback. Quantized strip writing fills the corresponding quarter-beat region. Delete removes that drum from future repeats while its existing voice tail can finish.

The public Original controls ignore pad presses during an active recorded touch and reject Hold-on while Overdub is enabled. The test retains the attempted Hold write and requires its observed zero readback. Hold writes outside that declared recording case retain their normal checks.

Custom strip beats now use the measured roll clock. All16 beat choices were exercised with Quantize off/on, Hold and repeated touch/position changes. The public RSD enum starts at1/2 beat; the project enum starts at1/32. The fixture converts their orders explicitly: Original0 maps to project8, and Original8 to project0. The production control continues to use its existing ascending beat choices.

The Original keeps rolls running at the last BPM while host playback is stopped. A host discontinuity beyond one beat relocates its timer; smaller callback discrepancies use its existing correction. Manual ticks must also update the last valid increment, otherwise resume can reuse a stale value from a fragmented callback. Tests include BPM changes, pause/resume, forward/backward seeks and new callback/event phases.

The fresh tests also caught a snare restart being cancelled when its old tail became silent during the five-block retrigger fade. Natural voice expiry now leaves a scheduled restart intact. A low-pitch, linear-envelope regression exercises that boundary.

## How the reference was checked

[`rmx_drum_gestures.py`](../../tools/rmx_drum_gestures.py) declares each program. Version3 of the native fixture adds eight beat assignments and explicit transport events while retaining the earlier fixture versions. A separately built reference host delivers and logs BPM, PPQ, seconds and playback state. Its static path was checked against the preceding host with identical audio and auxiliary state.

Read-only observers sampled command words, clock scalars and customization field names in the SHA-pinned Original. Observed renders were compared with ordinary renders before using the traces. No DSP state was written, no audio buffers were read by the observers, and no Original binary, instruction listing or recorded audio is part of the repository implementation.

Complete renders use fixed32/32 offsets, unchanged1% relative RMS gates for each channel, whole-output/one-second/event windows, and the existing absolute gate for silent channels. Optimized and ASAN/UBSAN complete WAV bytes must agree. There is no gain fit or alignment search.

## Boundaries

The recorder still requires the default beat assignments, manual120BPM, internal factory drums and default pitch ranges. Custom assignments are qualified for rolls separately. Combining custom assignments with recording, arbitrary transport motion during recording, non48k operation, external samples and physical controller/hardware behavior remain outside this campaign. Native strip/button events are distinct from AU/VST3 MIDI delivery.

The engine object is50,048 bytes, including2,776 bytes of bounded sequence state; it remains below64KiB. Prepared audio buffers are unchanged. The new strip path is covered by the callback allocation guard.
