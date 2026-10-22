# Loop tempo and pitch

Bank slot 1 loops now follow the engine tempo without multiplying the requested pitch by the tempo ratio. XPitch changes pitch independently. One-shots and captured input rolls retain their existing playback behavior.

## Reader

`LoopStretch` is a dependency-free time-domain overlap-add reader. It advances two positions independently:

- The source timeline advances by `source sample rate / engine sample rate * engine BPM / source BPM`.
- Each overlapping reader advances by `source sample rate / engine sample rate * 2^(XPitch / 12)`.

Readers crossfade over 20 ms with complementary smoothstep windows. At each crossfade boundary, a bounded waveform search aligns the incoming reader to the outgoing audio. The search covers at most 8 ms either side of the source timeline, evaluates at most 49 candidates, and compares 24 stereo probes per candidate. Both channels use the same position and window. The alignment score includes both channels, so opposite-polarity stereo does not cancel during analysis.

This reads immutable sample data directly. Each voice adds 32 bytes of state, with no audio buffers, heap allocations, locks or file access. All 32 voice states add 1 KiB to the engine. The maximum number of simultaneous bank loops remains four, one per bank. A repeated hit stops or restarts the existing loop instead of creating another stretched voice.

When pitch and tempo require the same source step, a newly started voice uses the original direct interpolation path. At neutral tempo and pitch, this preserves the original sample values without an extra processing delay. An active stretched voice retains its readers when controls move through neutral to avoid a sudden change of read position.

## Checks

Run:

```sh
cmake --build build --target rmx_sampler_tests rmx_memory_budget -j 4
./build/rmx_sampler_tests
./build/rmx_memory_budget
```

The sampler target checks:

- Original neutral interpolation, including fractional sample-rate steps and repeated wraps.
- Independent pitch at 70, 120, 180 and 240 BPM, with -24, -12, 0, +12 and +24 semitones.
- Pitch preservation across 8 kHz and 48 kHz sample assets when engine tempo changes from 120 to 180 BPM.
- Loop-envelope repetition timing at 180 BPM, independently of pitch.
- Stereo polarity and channel alignment.
- Four simultaneous loops, short and one-frame assets, source rates up to 192 kHz, rapid tempo changes, and -24/+24-semitone control changes.
- Zero instrumented `new` or `new[]` calls during the mixed-rate automation test.
- Existing pad/source routing, loop stop/restart, sequencer identity, state and bank-size checks.

On the development Mac, a Release run with four synchronized stretched loops at 48 kHz and 64 frames reported a mean callback time of 6.49 microseconds and p99 of 15.46 microseconds. The callback deadline was 1333.33 microseconds. This is a short synthetic benchmark, includes the engine, and does not establish real hardware performance or audio latency. The test prints current timing on each run rather than enforcing a machine-dependent threshold.

The existing embedded-memory check still passes: engine audio buffers occupy 26,721,456 bytes, and the engine plus 64 seconds of stereo assets occupies 51,896,496 bytes in the bounded SDRAM arena. The stretch state is part of the engine object and does not add arena allocations.

The sampler checks also pass in a separate Debug build with AddressSanitizer and UndefinedBehaviorSanitizer enabled. That run checks memory safety and undefined behavior; its instrumented callback timing is not a Release performance result.

The Daisy image also cross-compiles and links with this reader using the pinned Arm GNU 14.3 toolchain. A separate output directory keeps the normal firmware artifacts intact:

```sh
make -C firmware/daisy BUILD_DIR=../../build-sampler-arm -j 4
```

That build uses 47,576 bytes of SRAM, 203,368 bytes of QSPI flash, and the existing 60 MiB SDRAM arena. The build confirms ARM compilation, linking and static layout. It does not establish callback deadlines, stack high-water usage or playback quality on a board. Existing SDK startup FP-register, nosys syscall and RWX segment warnings remain.

## Limits

This is an original bounded implementation. It has not been matched against recordings from a hardware RMX-1000 and does not establish proprietary algorithm parity.

Negative XPitch means a lower musical pitch, not reverse playback. A reversed sample asset is read normally in its stored order. The reader supports positive source steps only, matching the current sampler controls.

Overlap-add can soften transients, produce a chorus texture on sustained or complex material, and move a local transient within a grain or alignment interval. The independent source timeline prevents cumulative tempo drift; it does not make every transient sample-accurate. Extreme pitch or tempo changes are less transparent. Linear interpolation does not provide an anti-aliasing filter for large upward pitch shifts. The synthetic checks establish pitch, timing, stability and resource behavior, not perceptual transparency on real music.

Listening comparisons, a musical test corpus, longer playback sessions and an on-device Daisy CPU measurement remain required before calling this production-validated stretching.
