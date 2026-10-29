# Trans/Roll reference matching

This work compares factory Default settings at 48 kHz and 120 BPM with the
original RMX-1000 Plug-in 2.2.0. The measured source is input-only, Scene is off
and Release is disengaged. Physical hardware and the whole device remain
unqualified.

The research implementation is in
[`TransRoll.h`](experiments/TransRoll.h). It processes source samples before the
common 32-frame transport, preserving the callback's unfilled startup slots.
The crossover and historical level detector follow the measured Gate/Drive
arithmetic. Knobs move by one raw step per block; raw 119 through 136 is neutral.

Trans combines an eight-stage pattern with a separate rhythmic mask. That mask
updates its phase every eight frames and fades transitions over 128 samples.
The Isolator's global grid uses the beat manager's separate 1/16-beat clock.
Entering Trans resets the shared grid tick and phase, including a negative phase
when the last grid edge is more than half a grid interval ago. Those resets also
affect later Roll boundaries.

Roll continuously records each band into a circular history. Starting a roll
rewinds to a detected transient, with at most 960 samples of lookback. It copies
32 stereo frames per block into a second ring, and plays three independent
readers. The grid arms their loop returns; each reader fades down before
returning to the beginning, then fades back up. Knob zones select and mix these
readers after their first loop becomes available. Recording only from the knob
event, or using a generic beat-length buffer, gives different attacks and loop
edges.

The first complete prototype passes all 26 discovery programs. Its largest
complete sample difference is 2.9802322387695312e-8, without full float-bit
identity. A subsequent frozen prospective set passes 8/28 repeated-throw programs
and 26/32 lifecycle programs. These failed recordings remain retained. They
expose the missing Trans grid resets. After correcting those resets and their
order relative to Roll initialization, all 86 existing programs pass as
development regressions. All 60 genuinely new programs in the second set pass the frozen correction.
All 146 programs also pass independent numerical score recomputation, with
complete optimized/sanitized WAV byte identity. The immutable local research
snapshot has manifest SHA-256
`4af060ad7488f3753fa8ca96846b0e3cc66b5976fb221a6462583252f61e00e2`.

Sparse read-only observations pin the original DSP executable by SHA-256 and
record only controls, timing, envelope values and pointer offsets. Completed
Low/0, Low/192 and corrected repeated-throw observations reproduce the ordinary
original audio and all five auxiliary artifacts byte for byte. One incomplete
Rosetta debugger stop contributes no result. Another repeated-throw observation
used the program source for a pulse-source plan: its audio differs, so that
observation is excluded and was rerun with the correct input. Vendor executable
instructions and audio are retained only in ignored local research storage.

## Live implementation

[`TransRoll.cpp`](../../src/core/TransRoll.cpp) runs the measured arithmetic on
the shared 32-frame engine clock, with contraction disabled. All 146 programs
pass again through the live engine and independent sanitized replay. Both AU
and VST3 pass all 146 original programs and the separate native-delivery limits,
plus 359 runtime checks per format. These are delivery regressions against the
same recordings, rather than additional prospective original captures.

Eligibility requires Default settings at 48 kHz, matching Isolator/Scene source
selections, manual tempo and 120 BPM. Other settings use the previous processor.
The reference corpus qualifies input-only, Scene off and Release disengaged.
Finite-output storage-transition tests do not extend that sound qualification.

The six long rings borrow the two legacy Isolators' twelve prepared history and
capture buffers. Legacy crossover states continue advancing while their storage
is borrowed. A small allocation covers the capacity difference, and a recent
history cache retains enough prehistory for a transient rewind when a loan begins.
History and capture validity are tracked without clearing whole rings during an
audio callback; withdrawing the loan invalidates the old interpretations before
legacy processing resumes. Prepared audio buffers increase by 245,376 bytes to
30,100,112 bytes. The host Engine object grows by 1,792 bytes to 44,736 bytes.
The 60 MiB arena test includes loan withdrawal through source, tempo and profile
changes, and reports zero callback allocations.

All 37 native tests and four selected sanitizer groups pass. Firmware source
lists include the new unit and arithmetic flag. The firmware host suite retains
its inherited `full_integration` factory-silence failure (15/16 pass). A new ARM
or physical-hardware run has not been qualified.
