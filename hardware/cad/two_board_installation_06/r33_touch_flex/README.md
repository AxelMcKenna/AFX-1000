# Constant-length touch-wire flex receiving study

This additive study moves the r29 connector wire-exit datums **0–1 mm in +Y**, at
fixed height and orientation, without moving the soldered D_J1009 or C3 J1
endpoints. It is a bounded geometric flex construction, not sourced JST release
travel or a complete service procedure. r32's prescribed 24 mm full-cradle
removal remains a separate rejected study. Controlled/measured mating axis,
contact registration, actual separation travel, latch access and grip volume
remain unknown. No source/header/module geometry is changed.

The host-side three-primitive tail changes its quarter-circle radius from 13 to
`13+t/(2-pi/2)` mm; adjacent straight lengths change to keep total length exact.
The frozen solder exit and first two arcs stay fixed. The outgoing initial
straight shortens by `t`. Four new tangent R13 arcs in its westward straight
store exactly `t` extra length: `4*13*(theta-sin(theta))=t`. At t=1 mm their
angle is 28.004963°, projected span24.416498 mm and peak height3.044420 mm.
They return to the original straight with the original tangent and height.
TH4's initial1.5 mm straight retains0.5 mm. TH1's shortest west straight24.5 mm
retains0.083502 mm after the bump; this mathematical margin is not an assembly
tolerance allowance. At t=0 the bump collapses continuously to the original
straight. All eight wire lengths, fixed endpoints, tangent joins and R≥13 are
checked at101 poses per wire, with the continuous identities stated above.

## Continuous collision coverage

`touch_flex_TH1` through `touch_flex_TH4` are **motion receiving supersets**, not
nominal static wires. Their union is `touch_flex_wires`.

- Source-tail point positions are affine in radius (and therefore t). Convex
  hulls between matching endpoint-pose chord segments cover every intermediate
  chord. The exact circular paths differ from these chords by at most0.005254 mm.
- The outgoing initial straight only shrinks. Its other original primitives
  stay fixed. Every point of the four-arc bump remains inside the rectangle
  above its original west straight, bounded by the maximum3.044420 mm rise.
  The rectangle is deliberately larger than the exact swept bump.
- Rotated fn32 spheres of radius0.665 mm retain an inscribed radius, after
  chord error, above the project0.65 mm wire radius (which itself exceeds the
  Alpha5854 maximum0.6223 mm insulation radius). Mutual checks use0.795 mm
  spheres; after the same errors they exceed0.775 mm, thereby testing at least
  0.25 mm separation between the0.65 mm wire envelopes.

Independent full-motion envelopes are compared, so an empty mutual
intersection covers arbitrary relative wire progress, not merely synchronized
sample poses. A collision of a conservative envelope would require diagnosis
and cannot automatically be called an actual wire collision.

Local native checks include the retained population, controls, sensor,
ground/support assemblies and the r31 cradle/strap. Full root assembly coverage,
wire strain relief, material fatigue, allowable force, solder preparation,
crimp/tooling qualification and physical motion/assembly tolerance remain open.
The two connector halves and their actual contacts are not modeled. The cradle
strap would need its separately qualified removal process before moving the
body; a wire-envelope pass cannot prove latch release or complete body travel.

No completed touch or panel wires are counted. No root selection is changed.
The exact JST drawing gate remains open; no supplier contact or form submission
was made.

## Verified local result

All six r1 intersections are empty: mutual expanded wire envelopes, population,
controls, sensor, ground/supports and cradle/strap. The positive swept envelope
is a closed99,398-triangle solid with zero degenerate triangles and zero bad
directed edges. `verification.json` binds all seven native jobs, recursive CAD
sources and result/log/mesh artifacts. Three mutations (wire length, fixed
endpoint and bend radius) are rejected. Run:

```
.venv/bin/python -m hardware.cad.two_board_installation_06.r33_touch_flex.verify
```

Self-review retained the distinction between wire flex and body/latch service,
and used independent continuous swept supersets instead of passing only a
finite set of synchronized poses. No actual connector release stroke is
inferred from the one-millimetre available wire motion. Larger travel is not
pursued without the missing connector authority; the next work returns to
remaining panel input routes.
