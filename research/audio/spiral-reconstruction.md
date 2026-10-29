# Spiral reconstruction — 29 October 2026

The held-control research renderer passes 1,709 original software-reference
programs: 512 Main positions, 512 pitch positions, 96 mixed controls, 397 unique
historical programs and 192 fresh programs. The
[summary](measurements/2026-10-29-spiral-static-v4-summary.json) links the complete
comparisons and independent audits. Both channels must pass whole-output,
wet-output and one-second waveform screens. Optimized and ASAN/UBSAN complete
WAV files are byte-identical throughout this set.

This is research evidence for Default settings, 48 kHz, 120 BPM and the checked
input route. It does not establish a perceptual similarity percentage, physical
hardware agreement or delivery in the playable Engine. The static campaigns use
AutoButton 1 and a silent preamble. Cold input, other profiles, other tempos,
routes and live wrappers require separate checks. Moving-control results below
belong to a separate candidate and must not inherit static qualification merely
because they share equations.

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
Static and moving-control candidates remain outside the live DSP until their
storage, lifecycle, wrapper and compatibility checks are complete.
