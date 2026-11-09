# Analog-control candidate 02 — not selected

TBP44 remains the selected board. This candidate closes 26 native connections,
reducing power-board opens from 2,237 to 2,211. Native geometry and schematic
parity findings are zero; ERC retains the same two warnings. This is not a
fabrication release.

Twelve support components move, with three board-face changes. Nine local
surface ground returns are now 1.000–1.281 mm instead of 4.389–14.137 mm.
R100 was reversed to face its ground pad toward U14. The candidate adds
73 tracks, 27 vias and seven quiet-ground regions, and replaces 81 tracks
and eight vias. The board has 46 zones and 7,206 captured copper objects.

[analog-connectivity-review.json](analog-connectivity-review.json) independently
proves the 26 intended joins and preservation of every other native group,
24 moved-pad identities/geometries, all part/netlist identities, all three
new star-only analog returns, and the four retained digital returns. The
U32 capacitor reference region connects through a dedicated quiet stitch to
the owned In1 field; it cannot return through main ground independently.
All ILM/DVDT paths have complete own-quiet adjacent-ground projection under
the declared same-net via-clearance exclusions. Thirty-one old zone fills
remain exact, and eight existing zones were refilled.

The broader [reference audit](analog-reference-review.json) prevents selecting
this candidate. Of 1,569 retained complete-reference cases, two regress:

- `9770d677-f9b1-5431-97a0-f8f2ad480648`, ANA_FOLLOW2 on F.Cu: 0.045128 mm²
  uncovered on In1, between U32.1 and its existing enable via.
- `43a4da19-9273-5f60-977c-c7474fca0eea`, AUX supply on B.Cu: 0.106226 mm²
  uncovered on In6, at the R95 supply escape.

Four of the 25 new non-ground paths also need reference correction: the U13
and U14 power-good escapes (0.103540 / 0.117161 mm² uncovered on In1), R96's
enable connection (0.145570 mm² on In6), and R100's enable connection
(0.544840 mm² on In6). These findings must be resolved without losing the
proven native joins, quiet ownership, or existing reference coverage.

Five current local copper views were directly inspected; see
[plots/analog-visual-review.json](plots/analog-visual-review.json). This is
local visual inspection, not full-board or installed mechanical acceptance.
The earlier `analog-core-*` crops omitted the western side because native SVG
coordinates are offset from board coordinates; use `analog-complete-*` views.

The first native candidate caught a shared-enable backbone mistakenly retired
with R100's old branch and two redundant same-face vias. Candidate 02 restores
the original backbone objects and omits those vias. No rule was disabled.

Next: correct the six reference gaps, refill/revalidate/recapture, repeat the
preservation and ownership audits, and inspect the revised copper before a
new selected checkpoint. Remaining board routing, approved ESS footprint,
load/startup/fault/thermal review, accepted stack/plating, installed housing
and harness fit, and manufacturing outputs remain unfinished.
