# Cut/Add reference reconstruction — 29 October 2026

Cut/Add is implemented in the shared live Engine for Default settings at 48 kHz,
manual 120 BPM and matching Isolator/Scene sources. Its measured qualification
covers the input-only route, Scene off and Release disengaged. Other tempos,
profiles, sample rates, routes and physical RMX-1000 hardware are unqualified.
A one-percent waveform RMS gate is an engineering screen, not a perceptual
similarity percentage or a whole-device accuracy score.

## Method and failed predictions

The reference is the original RMX-1000 Plug-in 2.2.0. The retained executable
SHA-256 is `dd4e41fb722fad41ec23a1d0389f0e1808355a753a1245778be465c741fb1ced`.
The Intel reference host is pinned separately. Capture receipts bind the input,
control plan, parameter delivery/readback, plug-in binaries, complete output,
initial/final state and final inventory. Original recordings and executable
inspection artifacts stay in ignored local research storage. The repository
contains our own implementation and numerical coefficients, with no vendor
executable instructions or recorded audio.

The process combined deterministic waveform experiments with read-only scalar
observations of filter coefficients, detector state and control transitions.
The completed neutral observation produces byte-identical audio and all five
auxiliary artifacts compared with its ordinary reference capture. The observer
never reads sample buffers. This establishes that the observed run preserves
that reference program; it does not qualify arbitrary debugger runs.

The neutral equalizer alone failed. Reconstructing the sixth-order crossover,
kick detector and manual filters first passed all 14 neutral/negative discovery
programs. Adding the measured seven-tap pattern passed all 26 discovery
programs. The first prospective set then exposed a missing startup and button
transition path: only 0/28 fresh and 1/32 lifecycle programs passed. These failed
predictions are retained rather than relabeled as successful fresh evidence.

The correction models the continuously warm Classic Isolator dry signal used
by Cut/Add's activation blend. Reusing raw input there was wrong. The corrected
candidate passes those 60 development regressions plus the 26 discovery
programs. It was then frozen before a second set of 28 fresh and 32 lifecycle
original recordings. All 60 new programs pass, bringing the candidate to 146.

All 146 research renders also pass a separate scorer and an ASAN/UBSAN replay.
Complete optimized and sanitized WAV files are byte-identical. The immutable
local snapshot is `build/artifacts/research/cut-v8-qualified-research-snapshot-20261029`
in the main checkout: 786 files, manifest SHA-256
`7600a48741604bdd0ad4471479a434584bc71a9046b90fb8b326f0220fa3cd4e`.

## Signal and control behavior

The processor runs on the Engine's common 32-frame clock, before Scene receives
its generated-source input. Source fades are applied once before the nonlinear
processor. Three raw band controls map to the original 0–255 positions, in
Hi/Mid/Low internal order. Cut slews by two raw positions per block, with one
step per 16-frame half. The manual-filter coefficient table has 128 Mid
high-pass rows followed by 128 Hi low-pass rows; interchanging them fails the
negative-control recordings. The header preserves numerical float32 values.

A sixth-order low-pass and high-pass pair splits the incoming signal. A linked
kick detector warms from the first block even while Cut/Add is disengaged. Its
low-passed stereo half-sum feeds a two-stage wrapping integer integrator/comb
reduction, asymmetric peak envelopes and the measured kick-suppression gain.
The detector gain is smoothed per sample. Explicit unsigned wrap and bounded
float-to-integer conversion preserve the observed arithmetic without signed
overflow or out-of-range conversion undefined behavior.

The low kick contribution is `low_pass * (detector_gain - 1)`. The remaining
signal is `high_pass - low_pass * detector_gain`, followed by a fine equalizer,
the Hi low-pass control and the Mid high-pass control. Each manual filter has a
squared dry blend and sample-interpolated target. Low gain uses the original
1/123 mapping below unity. Working biquad accumulators are double precision,
with float32 outputs and state storage at each 32-frame boundary; manual
filters and control arithmetic retain float32 sequencing. The production unit
is built with contraction disabled.

Add splits the residual into high and middle bands and uses the kick
contribution as its low source. Each band has seven eighth-beat-spaced taps,
3,000 through 21,000 frames at the qualified tempo. For depth
`d = clamp(raw - 131, 0, 124)` and `a = d * float32(3/124)`, the Default pattern
weights are `clamp([a-2,a-1,a-2,a,a-2,a-1,a-2], 0, 1)`. Above depth 62, the
measured depth correction scales those weights. All targets interpolate over
32 frames. Startup readiness and the five-block Add fade are separate states;
reading old ring contents before readiness is prevented from becoming audible.
The low Add return is scaled by 1.5 before the common float32 0.77 output scale.

The activation blend uses four continuously warm crossover filters and three
Classic dry gains. Those gains start at zero and ramp over 160 samples. They
use the requested controls directly; applying Cut's two-step slew to them
would change startup and gesture behavior. The dry reference depends on the
requested enabled state, while the wet path depends on the selected processing
state. Keeping those two clocks separate fixes the prospective failures.

## Live storage and validation

`CalibratedCutAdd` borrows the first three logical 196,608-frame rings from the
storage mapper already used by Trans/Roll. The effects are exclusive owners;
legacy Isolators invalidate their history metadata on ownership changes.
Trans/Roll continues warming its bounded recent-history cache while Cut/Add
owns the long rings. It seeds that recent history when ownership returns.
Cut/Add withdraws its selected state before another owner can reuse the pool.
No additional long buffer or callback allocation is introduced.

Prepared 48 kHz buffers remain 30,100,112 bytes. The host Engine object grows
from 44,736 to 46,016 bytes. The fixed-arena check exercises mode changes and
loan withdrawal via profile, source and tempo changes, verifies finite outputs,
and retains zero callback allocations.

The harness scores complete stereo renders after the fixed 32-frame capture
boundary and explicit startup, activation, held, return and control-event
windows. Each channel must meet the unchanged one-percent RMS gate, with an
absolute floor for effectively silent references. Candidate latency and gain
are never fitted to a recording. Full-file hashes retain the complete startup
and tail even where a diagnostic window begins later.

Reproduction uses `tools.rmx_cut_match` for frozen prediction, original capture
and comparison; `tools.rmx_cut_audit` independently rescoring and sanitizer
replay; and `tools.rmx_cut_plugins` for actual AU/VST3 normalized-control
delivery and reference comparison. Use `--live --regression` for the live
comparison and `--live` for its audit: delivery checks against existing
recordings are not new prospective original evidence. `tools.rmx_cut_trans_compat`
requires all 146 prior Trans/Roll programs to retain their whole WAV bytes.

The integrated native Engine, AU and VST3 each pass all 146 programs. Live
optimized/sanitized complete WAV bytes agree on all 146. The largest wrapper
sample difference from native is `5.546678239835239e-32`; both wrappers also pass
359 runtime checks. These wrapper renders reuse the original recordings and
are delivery regressions, not another prospective reference campaign.

The 37 repository tests and four selected sanitizer groups pass. The firmware
host suite retains its inherited `full_integration` factory-silence failure:
15/16 pass. There is no new ARM or physical-hardware execution claim.

The [live validation receipt](measurements/2026-10-29-cut-add-live-validation.json)
binds the complete reports, source closure, binaries and test logs. The stable
preview is `build/live-engine-preview-20261029-cutadd` in the main checkout.

Compatibility replays preserve complete previous audio for 836 drum programs,
146 Gate/Drive programs, 146 Trans/Roll programs, 89 pad-roll programs, 1,513
reverb programs and 216 Release programs. Drum, roll and Release replays also
require current optimized/sanitized whole-WAV byte identity. Release retains
complete float32 sample-bit identity against the original reference. The
inherited near-null mixed Crush wet-window failure remains failed; retaining
its previous audio does not turn it into a waveform-gate pass.
