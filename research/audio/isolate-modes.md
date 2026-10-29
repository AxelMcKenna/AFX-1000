# Remaining Isolator modes

This work compares our implementation with the original RMX-1000 Plug-in 2.2.0.
It does not establish equivalence to physical hardware or a percentage match for
the whole device. Gate/Drive now runs in the live engine for Default settings at
48 kHz with matching Isolator/Scene source selections. The measured scope is
input-only at 120 BPM, with Scene off and Release disengaged. Active Cut/Add and the Spiral models remain unfinished. Trans/Roll now also
runs in the live engine within its measured manual-tempo scope; see
[its method and qualification](trans-roll.md).

## Discovery

The first 78 programs cover Cut/Add, Trans/Roll and Gate/Drive. Each mode has two
neutral programs and 24 individual-band throws, using a varied-level stereo
program and sparse stereo pulses. All programs are eight seconds at 48 kHz and
120 BPM, with factory settings, input selected, Scene off and Release disengaged.
Controls move at sample 96079 and return at 240173. Callback sizes are 127 and
509 samples. One pulse at sample 31 checks startup behavior.

`tools/rmx_isolate_modes.py` checks the original binary, host, input samples,
parameter requests and readbacks, plans, receipts, state and output hashes. It
compares the recorded float output directly at the established 32-sample delay.
Acceptance remains 1% RMS error independently in each channel, for the complete
render and the pre-control, activation, held, return-edge and return windows.
No gain fitting, clock adjustment or reference-derived audio is used.

All 78 programs failed with the previous live implementation. This includes
neutral controls: normalized raw 128 is slightly positive, which incorrectly
starts a small roll or drive. Cut/Add also has a different neutral phase response.
The initial failed report is retained in `measurements/2026-10-29-isolate-modes-initial-comparison-failed.json`.

## Gate/Drive identification

The research implementation first reproduces the neutral crossover and startup
path. Startup source fading precedes the filters. Each crossover has two cascaded
biquads with measured float coefficients. The biquads retain double working
state within a 32-sample block, round their outputs to float and store float state
at the block boundary. The quiet-input path is also reproduced. Algebraically
equivalent refactoring changes rounding, so the calculation order is explicit.

The internal order is high, middle, low. The public controls are low, middle,
high; the fixture reverses the order explicitly. Gate/Drive has a wide neutral
region, one raw control step per block, side changes at the neutral boundaries,
and a five-block transition between the neutral and processed band. Factory
settings select internal depth profile zero.

The detector keeps a peak across each 50-block interval, a 24-entry history,
a held level and a timed decay. Its history starts at 0.05 rather than zero.
That initial condition matters even several seconds later: a zero-filled history
caused the last failing middle-band pulse test. The first history interval also
has distinct warmup behavior. The implementation preserves the observed history
scan extent and update order.

Gate compares an interpolated historical level with a stereo-linked envelope,
then applies the measured opening and closing curves. Drive ramps its input gain,
clips against the interpolated level, filters the clipped signal and ramps its
output gain. Low Drive has another low-pass stage before clipping. This is not
equivalent to a generic gate threshold or a tanh distortion.

Sparse read-only observations record controls, coefficients and envelope state,
never sample buffers. The original binary is pinned by SHA-256. Both completed
observation runs preserve the complete ordinary reference audio and all five
auxiliary artifacts byte for byte. An intermediate custom trace with a nonzero
initial block selection exposed a missing initial debugger skip; its block labels
were rejected and the corrected observation was rerun. The default trace beginning
at block zero was unaffected.

Development progressed from 22/26 Gate/Drive programs passing to 25/26, then
26/26 after correcting the detector history initialization. The largest relative
error among those development windows is 0.0000529167 (0.00529167%), in a
neutral startup pulse window. This is a development result, not independent
qualification. At that stage Trans/Roll reproduced its two neutral programs only;
its active matching is documented separately. Cut/Add remains unfinished.

## Independent checks

The next stage freezes 28 outputs before recording new original references. It
uses new deterministic chirped/noisy stereo and pulse sources, callback sizes
16/63/257/1024, near-boundary control values and repeated throws on all three
bands. Every control edge and subsequent held interval is checked as well as
the full render. Frozen source, binary and prediction hashes must remain intact.
Results will be recorded separately; no passing result is assumed in advance.

The first fresh set passed 13/28. It exposed a research-fixture error: filtering
the already transported neutral output loses the first block's filter history
and puts startup samples in the wrong callback slots. The corrected fixture
processes input blocks before transporting their output, retaining the actual
unfilled startup slots. This did not change the live engine's transport.
Twenty-seven programs then passed. The remaining throw exposed a different
detector decay while a Gate knob is neutral; retaining that state resolved it.
All 28 former fresh programs now pass as development regressions. The failed
prospective report remains recorded and is not relabeled as independent evidence.

A second set freezes 28 new predictions before recording new sources and
programs. It includes raw 107/108/147/148 boundary settings and callbacks
33/79/513/4093. [All 28 pass](measurements/2026-10-29-gate-drive-fresh2.json).
The 26 discovery, 28 former fresh and 28 second fresh programs also pass an
independent numerical recomputation. Their complete optimized/sanitized WAVs are
byte-identical in all 82 programs, with the core and research processor built
under address and undefined-behavior sanitizers. Independent reports are
[discovery](measurements/2026-10-29-gate-drive-discovery-audit.json),
[former fresh](measurements/2026-10-29-gate-drive-former-fresh-audit.json), and
[second fresh](measurements/2026-10-29-gate-drive-fresh2-audit.json).

The final v5 research model differs from original samples only in very small
filter tails: the largest absolute difference across the 82 complete renders is
3.47e-35. This is not full float-bit identity. The immutable local v5 snapshot
contains all bound source files, binaries, comparisons and sanitizer replays;
its 531-file manifest SHA-256 is
`b161fe13252edefbb3b35164df9974f3b9e1b7358cd0cac8ef87bba3fe9c6321`.
Subsequent work adds on/off and cold-control initialization checks before live
integration. Other rates, tempos, user profiles, source combinations and physical
hardware remain outside the current measured scope.

## Interrupted activation

The first 32-program button/cold-control set passed 31 programs. The retained
[failed report](measurements/2026-10-29-gate-drive-first-lifecycle-failed.json)
includes initial active knobs, button cycles, cold activation and short touches.
A 159-sample early touch followed by a later low-band Gate activation fails.
Sparse original-state observations preserve the ordinary audio and show why:
Gate initialization resets the threshold level, target and countdown, but leaves
the previous per-sample threshold increment intact. If the next target equals the
initialized target, that old increment keeps running without a countdown. In
this recording the threshold becomes negative and the gate opens. Clearing every
field during initialization would produce different audio.

The model now retains that increment and initializes band controls on the first
actual Gate processing block. All 32 former button programs pass as development
regressions. A further new set is predicted before capture to check this behavior
with new sources, timings, raw controls and callback sizes. These are original
plug-in observations; the same quirk has not been established on physical hardware.

## Live delivery

The second button set passes all 32 genuinely new programs. This brings the
Gate/Drive corpus to 146 programs: 26 discovery, 28 former fresh, 28 second fresh,
32 former button and 32 second button programs. The algorithm was frozen before
the second fresh and second button recordings; live integration and wrapper
checks reuse these recordings as delivery regressions.

[`GateDrive.cpp`](../../src/core/GateDrive.cpp) implements the measured arithmetic
outside the adapter, with contraction disabled. The shared engine clock supplies
complete 32-frame blocks. It combines the selected input/pad signal before this
nonlinear processor, preserves bypassed sources, and feeds its already faded
output into Scene's generated-source input. The other profiles and rates retain
their previous processors. Source combinations beyond input-only are not qualified
by this corpus.

All 146 live programs pass the unchanged original-reference gates and an
independent score recomputation. Every complete optimized WAV equals its
sanitized replay byte for byte. Both AU and VST3 pass all 146 original programs,
the separate native-delivery limits, and 359 runtime checks each. The largest
wrapper/native sample difference is 5.662441253662109e-7; every scoped wrapper
receipt reports 32 frames of latency. Runtime smoke checks at other rates do not
establish sound matching at those rates.

The first wrapper replay failed one near-silent held window in each format:
relative error 4.81%, absolute RMS error 5.23e-13. The 0 dB request is 2/3 of the
normalized host gain range. Its float round trip decoded to a tiny nonzero dB
value, affecting the later gate tail. The adapter now caches the host's actual
decoded unity point and maps that exact point to zero dB before preparing and
processing the engine. This preserves continuous values around it and requires
no fitted gain or acceptance change. Both failed reports and the first adapter
source are retained; the final wrapper replay passes all programs.

The native repository's 37 tests pass, as do four selected sanitizer groups.
Prepared audio-buffer allocation is unchanged at 29,854,736 bytes. The host
Engine object grows from 41,792 to 42,944 bytes, and the bounded arena check
still reports zero callback allocations. Firmware source lists include the new
unit and arithmetic flag. The firmware host suite retains its inherited
`full_integration` factory-silence failure (15/16 pass); a new ARM/hardware
execution has not been qualified.

Compatibility replays preserve the complete earlier audio: 836 dry/moving/drum-FX
programs, 89 roll programs, 1,513 reverb programs and 216 Release programs. The
known near-null Crush wet-window failure remains failed. The Release replay also
retains complete float32 sample-bit equality with its original references.

The unchanged original recordings and executable inspection artifacts remain in
ignored local research storage. Vendor executable instructions and audio are not
included in the repository.

The [live validation receipt](measurements/2026-10-29-gate-drive-live-validation.json)
binds the source, final reports and test logs. The local delivery archive contains
15,074 files; its manifest SHA-256 is
`23f74414dd078ee3db3e5676c70c21b6bda80afca17e5e5462c10147c8826513`.
The stable preview is `build/live-engine-preview-20261029-gatedrive` in the main
checkout.

## Cut/Add reconstruction

The [Cut/Add research record](cut-add.md) documents the crossover, continuously
warm kick detector, manual filters, seven Add taps and Classic dry transition
path. Its corrected research candidate passes 146 original-reference programs,
including 60 genuinely new programs recorded after predictions were frozen.
Independent scoring and sanitized replay agree on all 146. The earlier failed
60-program prediction remains retained. Live integration shares the existing
Trans/Roll delay-storage pool; other tempos, profiles and hardware remain
unqualified. See the Cut/Add record for the precise signal and storage rules.
