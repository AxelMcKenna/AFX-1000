# Spiral reconstruction — updated 30 October 2026

Spiral Up and Down now run in the playable Engine for Default settings at
48 kHz and manual 120 BPM. The live Engine passes 1,709 held-control reference
programs and 336 moving-control, startup and direction-switch programs.
All 2,045 optimized/sanitized complete WAV pairs are byte-identical. The
held-control live renders also retain the complete research-renderer WAV bytes.
The reference is the original RMX-1000 Plug-in 2.2.0; these results do not
establish a perceptual percentage or physical-device equivalence.

The 1,709 static cases comprise 512 Main positions, 512 pitch positions,
96 mixed controls, 397 unique historical programs and 192 fresh programs.
All static and dynamic cases use the same production Spiral implementation;
each fixture prepares a fresh Engine.
The 336 dynamic cases comprise eight retained campaigns (320 cases), including
previously failed predictions replayed as regressions, and a new independent
16-case live-Engine holdout. Counts describe distinct programs rather than
unseen successes: earlier failed predictions remain failures in their original
reports. Both channels must satisfy the unchanged whole-output, wet-output,
one-second and event-window gates wherever applicable.

The qualified audio route is input-only, with other effects disengaged. Other
sample rates, tempos and User settings retain the existing Spiral implementation.
Their sound and combinations with drums/Isolator/Release require separate
reference qualification. The implementation uses the actual shared 32-frame
Engine transport; no per-case gain fitting, wet alignment or latency search is
introduced. The earlier research campaigns are described below in their original
chronology and evidence scope.

## How the missing behavior was found

The earlier model passed only 285/361 programs. Quiet impulses and carefully
controlled stereo cues had exposed useful components, but an empirical output
filter hid the actual topology. Its failures remain documented in
[the historical component investigation](spiral-core.md).

The replacement uses deterministic audio experiments and bounded, read-only
scalar observations from the original RMX-1000 Plug-in 2.2.0. The original
executable SHA-256 is
`dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced`.
The observer pins that binary before collecting selected clocks, coefficients,
gains and ring offsets. It never reads sample buffers. Complete observed audio,
control plans, parameter logs, initial/final state and final inventories are
compared byte for byte against ordinary captures. That check establishes that
the particular observation preserved its reference program.

The decisive missing stage was the filter after the pitch reader. Replacing the
empirical 32-tap correction with the observed biquad, preserving float32 outputs
and block-boundary state rounding, resolved the old 361-program failures. The
working biquad accumulators use double precision; the production-style arithmetic
and control paths retain their observed float32 operation order. Floating-point
contraction is disabled for the experimental renderer.

The apparent fractional-delay drift comes from repeated float32 additions of
`2.0833333564951317e-6` and reflection at ±1. A fitted constant had approximated
the rounding drift, but did not reproduce its cause. The first private Spiral
block starts after the first common 32-frame block. Starting its clock at input
frame zero changes later repeats.

Main scales newly admitted input rather than the settled feedback signal. The
feedback gain includes a baseline of 0.8, with an additional Main-controlled
0.7 for Up or 0.4 for Down. Omitting that baseline caused 50 low-Main failures
in the first prospective sweep. The complete first predictions passed 462/512
Main, 512/512 pitch and 65/96 mixed programs. Those 81 failed predictions remain
failures. After correcting the gain, transport and return activation, a new set
of 192 predictions was frozen before the corresponding original recordings;
all 192 pass the independent audit.

## Callback transport was checked separately

Large, irregular callbacks exposed an error even when Main produced dry output.
The common processor collects 32 input frames while emitting any pending output.
Slots not yet filled by processed output retain raw input. Consequently a nominal
32-frame latency is not a uniform shift at every partial callback boundary.
The reference host also splits callbacks at exact parameter-event frames.

The research renderer now reproduces that FIFO protocol. This was independently
checked with every effect disabled against the actual Engine: callbacks of
8, 17, 31, 32, 79, 127, 263, 1021, 1024, 2047, 4092, 4093 and 4096 frames produce
complete float32 sample-bit-identical bypass output. No wet alignment, fitted
gain or per-case latency adjustment was introduced. Comparisons retain the
declared fixed 32/32 boundary convention.

## Moving controls and buttons

The development motion model is
[SpiralMotion.h](experiments/SpiralMotion.h), rendered by
[spiral_motion_probe.cpp](../../tools/spiral_motion_probe.cpp). Eight discovery
programs cover Main, pitch, time and repeated effect off/on in each direction.
Candidate v8 passes all eight: Main, pitch and button outputs are sample-for-
sample identical; time programs have maximum wet relative RMS error about
`1.07e-7`. These are discovery results, not fresh qualification.

Main slews by one raw position per 32-frame block. Its delay target follows the
requested value through a separate velocity and acceleration law. The delay
read cache is anchored before that update, and sample offsets are relative to
the first newly computed integer index. Anchoring every read directly to the
new delay was audibly wrong during Main movement. The output gain regulator
also moves much more slowly than the input gain: its per-sample step is the
remaining difference divided by 96,000, rather than by 32.

The pitch reader keeps its fractional phase across knob changes. Its overlapping
two-head windows have separate Up/Down durations and a polynomial whose weights
can sum to 1.5; normalizing them changes the original response. The four returning
echo lines receive separately weighted input streams. Applying weights only
when reading a shared stream matches held controls but fails time gestures,
because it changes the history of existing tails.

With AutoButton 1, effect-off fades newly admitted input over 160 samples while
the delay and pitch clocks keep running. It also changes the inner feedback
coefficient. Re-engaging restores input and resets the clipping threshold from
1.5 times a separately smoothed activity measurement, bounded by unity and the
current input floor. Resetting the threshold to zero passes an early re-arm but
fails later re-arms after the input has become quiet. Keeping those failures
as separate checkpoints prevented a misleading aggregate pass.

A fresh 64-program campaign combines independent source audio, boundary control
positions, simultaneous gestures, repeated buttons and callbacks from 8 to
4096 frames. Its source, candidate binary, schedules and complete output
predictions are sealed before any original recording. Its first candidate passed all 32 single-control programs but failed all 32
combined programs. The failures exposed a separate 160-sample input gate on
the four echo-return lines. Adding that gate passes 56/64 development regressions, with byte-identical
optimized/sanitized output on all 64. Eight Down programs still fail; they expose
a distinct dry-gain fade when buttons and Main move together.
The failed prospective audit is retained in
[the v9 report](measurements/2026-10-29-spiral-motion-v9-fresh1-rejected-audit.json);
the corrected results are
[development regressions](measurements/2026-10-29-spiral-motion-v10-fresh1-regression.json).
A second, independent set of 64 combined programs is frozen after that correction
and before its original recordings. That candidate passes 42/64; all 22
failures are Down programs. These failed prospective results remain separate
from later corrections. The dry-gain correction then passes both sets as
64/64 and 64/64 development regressions. All 128 optimized/sanitized complete
WAV pairs are byte-identical. These regressions do not turn the earlier failed
predictions into fresh successes.

A separate 32-program nonzero-input startup discovery passes after adding the
private/common activation gains, the raw-history startup blend, primary delay
readiness and echo-return activation from zero. Its
[complete audit](measurements/2026-10-29-spiral-cold-v13-discovery.json) includes
startup and tail windows and complete optimized/sanitized WAV byte identity.
A third fresh set exercises 64 independently generated 32-second programs,
including cold input, combined gestures and the slow clock reversal; its result
initially passes 61/64. The three failed Up tails expose an arithmetic-order
difference during primary-delay startup: the original applies the readiness
gain to each interpolation term before adding them. Applying that gain after
the sum leaves a tiny rounding difference that can grow through Up feedback.
Preserving the original order passes all 64 as development regressions, with
byte-identical optimized/sanitized WAV files. The
[failed predictions](measurements/2026-10-29-spiral-motion-v14-fresh3-rejected-audit.json)
and [corrected regressions](measurements/2026-10-29-spiral-motion-v15-fresh3-regression.json)
remain separate. A final 32-program independent cold/long holdout is frozen
after this correction and before its original captures. All 32 new programs
pass, including whole/wet, one-second and event windows and complete
prediction/native/sanitizer WAV byte identity. See the
[fresh holdout audit](measurements/2026-10-30-spiral-motion-v15-fresh4-audit.json)
and [immutable research snapshot](measurements/2026-10-30-spiral-motion-v15-snapshot.json).
This result qualifies the research candidate in the declared scope; it does not
qualify live Engine integration or physical hardware.

## Reproduction and evidence boundaries

`tools.rmx_spiral_programs` defines static sources and control recipes;
`tools.rmx_spiral_static_match` verifies reference identity and control delivery.
`tools.rmx_spiral_prospective` seals predictions and independently audits fresh
static captures. `tools.rmx_spiral_static_audit` rechecks historical programs.
`tools.rmx_spiral_motion_prospective` performs the separate moving-control
prediction/capture/audit sequence. Each checker binds its inputs and source
hashes and rejects changed artifacts.

The recorded Python environment is 3.12.13 with NumPy 2.5.4, matching the locked
project dependencies. Build the motion research probe with C++20 and contraction
disabled, linking the existing `rmx_core` library. For example, after configuring
and building `build/core` on macOS:

```sh
c++ -std=c++20 -O3 -ffp-contract=off \
  -isysroot /Library/Developer/CommandLineTools/SDKs/MacOSX.sdk \
  -Iinclude tools/spiral_motion_probe.cpp build/core/librmx_core.a \
  -o build/core/rmx_spiral_motion_probe
uv run --locked python -m tools.rmx_spiral_motion_fresh4 predict \
  --session captures/spiral-fresh4 --renderer build/core/rmx_spiral_motion_probe
uv run --locked python -m tools.rmx_spiral_motion_fresh4 capture \
  --session captures/spiral-fresh4 --host "$RMX_REFERENCE_HOST" \
  --plugin "$RMX_REFERENCE_PLUGIN"
uv run --locked python -m tools.rmx_spiral_motion_fresh4 audit \
  --session captures/spiral-fresh4 --host "$RMX_REFERENCE_HOST" \
  --sanitizer build/core/rmx_spiral_motion_probe_asan --output checks/spiral-fresh4
```

The sanitizer executable is built separately at `-O1 -g` with
`-fsanitize=address,undefined -fno-omit-frame-pointer`, contraction disabled and
the correspondingly sanitized core library. The audit checks that both sanitizer
runtimes are linked. Use a new session/output directory for each run; existing
artifacts are deliberately not overwritten. The pinned reference host/plugin
must be available locally; they are not shipped by this repository.

Reference executables, recordings, debugger traces, private executable inspection
and compiled candidates remain in ignored local artifacts. This repository
contains our own code, numerical coefficients, methods and measurement reports.
The rejected static-v2 snapshot retains 2,409 files with manifest SHA-256
`19818305817bc135c4b5ec0d959d2f045dbaef6f3486762585aef0d65cfe3eda`.
The bypass proof is retained locally in
`build/artifacts/research/spiral-bypass-transport-20261029/verification.json`.
The earlier snapshots preserve the research stage before live adoption. The
30 October live qualification below supersedes that delivery boundary within
its explicitly measured scope.


## First activation and switching direction

Initially disabled programs exposed a distinction between warming raw input
history and starting the private effect. The first engagement emits the raw
source through the common 160-sample fade. The private delay, pitch and return
state starts on the following 32-frame block. A versioned schedule now expresses
initial enable state explicitly; 16 predictions sealed before the original
captures pass after this correction (v16).

Direction selection is another state transition rather than an ordinary pitch
knob change. The original host plan releases the old effect button and presses
the new button at the same frame. The common wet path fades out, then the private
processor restarts with a fresh dry fade. The first v17 prospective switch set
passed 11/16. Its five failures are retained. They exposed two missing details:
the dry fade restarts on the next block, and the pitch ring's audio survives
Up/Down switches even though its cursors, fractional phase, windows and filters
restart. Clearing that ring would remove audible history from the new direction.
The corrected v18 passes those 16 as regressions, then passes a separately
sealed 32-case holdout covering early, initially disabled, interrupted and
combined selector/control changes. No failed prediction was relabeled fresh.

## Storage and real-time integration

[CalibratedSpiral](../../include/rmx/CalibratedSpiral.h) and
[Spiral.cpp](../../src/core/Spiral.cpp) implement the identified arithmetic in
production code. Long buffers are spans into legacy Scene storage: 132,880 stereo
frames from the unused echo allocation and 32,768 raw-history frames from the
legacy pitch allocation. Primary history needs 32,768 frames because the largest
identified delay is below 24,064. Four return lines retain their individual
24,004-frame histories. No reference samples or rendered output are embedded.

Ownership changes invalidate the legacy delay metadata. Written-age guards make
unwritten borrowed primary/raw/return storage read as zero. A 4,096-bit validity
map does the same for pitch history without clearing a large buffer inside a
callback. Direction changes preserve that map; relinquishing storage invalidates
it. The raw input history stays warm while another Default Scene effect runs.
Storage withdrawal, reset, poisoned storage and unsupported-profile/rate/tempo
fallbacks are exercised by the dedicated storage test.

The prepared audio-buffer allocation remains 30,100,112 bytes. The Engine object
is 47,168 bytes (previously 46,016); CalibratedSpiral is 1,128 bytes. With factory
assets and the 64-second stereo sampler the prepared total is 56,000,912 bytes;
the measured peak is 56,173,712 within the 62,914,536-byte arena. The callback
allocation check observes zero global or PMR allocations. Spiral arithmetic is
compiled with floating-point contraction disabled in both desktop and firmware
host builds. These are storage/build checks, not an embedded execution deadline
or physical-board audio qualification.

## Live reference and wrapper reproduction

The excluded CMake targets `rmx_spiral_engine_probe`, `rmx_spiral_core_probe` and
`rmx_spiral_research_probe` build separate delivery layers from the same fixture.
Live audits require the Engine processing symbol, bind source and executable
hashes before/after the run, and compare independently retained original audio,
inputs, control plans, receipts and auxiliary state. The fresh 16-case Engine
holdout additionally requires complete sealed-prediction/native/sanitizer byte
identity before a prospective pass. It includes frame-zero input, initial off,
1/9/17-frame button touches and combined direction/knob changes.

`tools.rmx_spiral_static_motion_audit` replays the static corpus through the
stateful live processor. `tools.rmx_spiral_motion_regression` and
`tools.rmx_spiral_cold_match` replay the dynamic/cold reference sets.
`tools.rmx_spiral_engine_holdout` performs the fresh prediction/capture/audit
sequence. Use new output directories and retain the pinned original host and
plug-in locally. `tools.rmx_spiral_plugins` binds an explicitly supplied project
AU/VST3 bundle to the native qualification, checks parameter delivery/readback
and latency, and applies independent original-reference and wrapper/native
gates. Gain uses the plug-in's decoded 0 dB parameter value, not an approximate
normalized setting.

Wrapper captures are retained losslessly as a native WAV base plus a gzip stream
of PCM-byte XOR differences. RIFF prefix/suffix and SHA-256 checks preserve the
entire WAV, including subnormal values. Packaging is performed only after the
ordinary captured WAV has passed its audio checks, and unpacking must reproduce
its complete bytes. This reduces duplicate local storage without changing any
audio, error metric or threshold. Restore a retained wrapper WAV with:

```sh
uv run --locked python -m tools.wav_delta path/to/case/audio.delta.json restored.wav
```

The metadata and its adjacent native base/XOR stream must stay together.
APFS copy-on-write copies similarly preserve already byte-verified identical
native/sanitized outputs; the archive records source hashes and relocation.
Reference recordings, original executables and compiled binaries remain in
ignored local artifacts. Numerical reports and our own reconstruction code are
tracked in Git.


## 30 October delivery results

Both explicitly hosted formats pass 1,789 reference programs each: all 1,709
static cases, the 16 new Engine holdouts, 32 selector cases and 32 long/cold
cases. These are delivery regressions against the retained original recordings,
not additional unseen Original programs. Each format also passes all 359 runtime
checks. The largest wrapper/native absolute sample difference is
`1.1175870895385742e-8`; the largest relative RMS difference is
`7.394251084274274e-10`. Both are below the separately declared `1e-5` delivery
limits. Reported latency is 32 frames. This qualification uses the explicit
project bundles in the local capture host; it is not an every-DAW or controller
qualification.

All 38 native tests and five selected ASAN/UBSAN test groups pass. Firmware host
checks remain 15/16: the inherited `full_integration` failure reports
“Full engine factory path is silent.” The desktop factory-drum/reference probes
are separate evidence. Both firmware Makefiles and host CMake include Spiral
with contraction disabled; no new ARM image, board execution or real-time
hardware result is claimed.

To hear the measured Spiral path in the preview, use 48 kHz, Default settings,
turn AUTO BPM off and set 120 BPM. Select Spiral Up or Down, enable Scene FX and
use input audio with the other effects disengaged. Unsupported settings continue
through the earlier implementation.


The integration also preserves all 836 earlier drum programs byte for byte in
both optimized and sanitized renders, including the 224 dry, 44 gesture and
568 combined drum/Scene cases. Their prior scores transfer unchanged: 835 pass
every raw gate, while `drum-fx-live-effect7-route1` retains its microscopic
near-null wet-window failure. All 568 combined whole-output gates still pass.
All 89 drum-roll programs and their dry traces remain byte-identical. All 216
Release renders retain complete float32 sample-bit identity with the Original.
The 1,513 reverb renders retain their qualified complete WAV and dry-trace bytes.
All 146 programs per Gate/Drive, Trans/Roll and Cut/Add retain complete qualified
parent WAV bytes in native and sanitized builds, with an additional strict
438-program sanitizer replay requiring empty diagnostic output. These are
compatibility replays of earlier scopes, not fresh original captures or new
combined-Spiral qualifications.

The [live validation record](measurements/2026-10-30-spiral-live-validation.json)
links complete numerical reports, retained report hashes, compiler/source
bindings, runtime checks and the archived failed v17 prediction. Tracked reports
keep every field and numeric value, with one compact case per line; the record
pins both their Git copy and the byte-exact original local report. The local
archive is `build/artifacts/research/rmx-spiral-live-20261030`; playable bundles
are in `build/live-engine-preview-20261030-spiral`.


The stable local app and AU copies have their ad-hoc resource envelopes sealed.
Before/after checks require every Mach-O section's bytes, address, offset and
flags to stay identical. The signed AU is then checked again against the same
16 Engine holdouts and all 359 runtime assertions. This is a packaging replay,
not 16 new Original programs. The VST3 copy already has a valid resource seal
and remains byte-identical to its full qualification. The regular
[Mac packager](../../tools/package_macos.py) also signs and strictly verifies
copies without changing the source build products. The local preview is not a
notarized release.
