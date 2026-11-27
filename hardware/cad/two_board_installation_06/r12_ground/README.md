# Button-ground daisychain receiving candidate

This revision reduces the previous 26 ground junctions and 57 wires to **one
junction and 32 wires**, serving all 29 buttons and both selector commons. It
preserves five independent header feeds; each external terminal has one wire.
Intermediate buttons receive ground at terminal 3 and continue through the
manufacturer-documented always-connected terminal 4. The last terminal 4 in
each seven-button chain is unwired. Scene 9 continues to the one three-way splice
for the selector returns. This supersedes the r10 “terminal 4: no external wire”
assignment for intermediate buttons; the frozen r10/r11 files are not rewritten.
The panel electrical drawing must adopt this revision before release.

`ground-routes.json` supplies actual world coordinates and a route for each
individual wire, with 29.5, 28 and 31 mm routing planes. `routes.scad` exports the
32 wire receiving envelopes and the single splice reservation. The selected
Alpha 5853 source specifies 0.039±0.004 inch insulation OD (1.0922 mm maximum);
the model uses 1.2 mm diameter. The splice reservation is 25 mm long by 6.2 mm
maximum diameter, centered at [310,42,29.5], along X. Those are project receiving
limits, not verified final crimp/sleeve dimensions.

This is a **physical routing candidate, not a finished harness or cut list**:

- Paths use sharp polyline swept envelopes. Formed bend radii, supported curves
  and slack for opening the lid have not been resolved. The route lengths are
  centerline planning lengths, excluding preparation and service allowance.
- The minimum modeled wire-to-wire surface gap is only 0.11186 mm. Actual
  positioning tolerance and restraints must establish a defensible margin.
- Switch orientation is newly explicit: viewed from the underside with the
  OMRON logo upright, screen-right maps to local -X, screen-up to local +Y;
  apply each button's schedule rotation. Confirm 1–2 and 3–4 continuity unpressed,
  and isolation of 1–3 until pressed, before assembly. Terminal Z31.6 is a joint
  receiving datum, not a qualified solder-joint process or lead tolerance.
- **D_J2003 is still a generic, unselected 1×5 header.** Its route begins at the
  project wire datum [244,51,27.04]. No compatible female, seated stack or
  board-to-wire transition is certified. The other four feed wire datums also
  inherit the six-mate revision's conditional stack/retention requirements.
- The modeled switch leads, wire solder joints, insulation recovery, strain
  relief, fault-current behavior and pull/continuity acceptance remain open.
- Anode, LED sink, button-signal and potentiometer wiring remain separate work.

## Verification scope

`verify.py` independently traverses external wires plus the exact 29 internal
3–4 links and checks all 31 receiving endpoints against the frozen panel
contract. Wrong contact-pair and doubled-contact mutations reject. It checks all
496 distinct wire pairs using minimum 3D segment separation. This is an
independent geometric calculation over the modeled paths, not a native Boolean.

Pinned Linux OpenSCAD native revision r2 checks have empty intersections against:

1. Frozen local housing, holders, rear plate, lever bracket, board screw heads
   and selector brackets/boards/bodies/fasteners.
2. PCB component/tail and other context reservations, retaining conservative pot
   and sensor allocations. Only obsolete generic switch/holder context boxes are
   replaced by the exact holder sources in check 1; switch bodies begin above
   the candidate's maximum button-joint Z32.2.
3. All six frozen panel mating connector reservations.

The full current root assembly—including later LED carriers, exact sensor
ribbon, cooling harness and moving parts—has **not** been checked against these
routes. Import through the separate `workflow_adapter/ground-registry.json` as
conditional receiving geometry, then run those additional intersections.
No blanket contact exclusions are allowed. Own splice-port contacts are local
intentional terminations; connector and selector exits require later exact
terminal-region contracts.

The original failed allocation check is retained under `native/allocations`:
it detected 118.86 mm³ against old generic switch boxes and pot boxes. Revision
r2 replaces only obsolete switch/holder boxes with exact geometry, routes around
retained pot boxes and separates formerly crossing wires. Original failed
checks are historical; use fresh r2 source hashes for the current candidate.

The combined positive STL is nonempty but **not a closed oriented boundary**
under the repository mesh audit (10 excluded degenerate triangles / 10 bad
edges). It must not be used as a mesh Boolean obstacle. The three clearance
checks above evaluated the original SCAD sources directly and were empty.
Keep the source geometry for integration; this STL is only a visual witness.
