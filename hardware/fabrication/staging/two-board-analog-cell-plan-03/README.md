# Analog control routing candidate 03

TBP44 remains the selected board. This package is a construction candidate,
not a native-validated board or a fabrication release.

The plan moves twelve local support components around U13, U14 and U32,
including three changes of board face. Its 43 paths comprise 100 proposed
tracks and nineteen vias. It replaces 83 existing tracks and nine vias,
including the old R98–C39 connection, three remote enable-pulldown branches,
two power-good pin escapes, and one obstructing PG1 inner-layer branch.
Component values, packages and schematic nets remain unchanged.

R98 is reversed relative to placement 01, shortening its controller connection
from 6.994 mm to 2.802 mm. Both PG1 branches now avoid the required quiet ground
beneath the ILM/DVDT routes. The original routing candidate passed ordinary
geometry screens but failed this reference check; its findings are preserved
in [plan 02](../two-board-analog-cell-plan-02/README.md).

[geometry-review.json](geometry-review.json) verifies the twelve native KiCad
poses and 24 pad positions/net identities/sides, provisional local mechanical
clearance, proposed pad/track/via geometry, separate quiet-ground ownership,
and physical contacts restoring both power-good nets. It includes 593 nearby
copper and route-pair checks. The exact native poses are retained in
[native poses 02](../two-board-analog-cell-native-poses-02/README.md); the component
positions are unchanged between plans 02 and 03.

[quiet-region-screen.json](quiet-region-screen.json) checks six minimum
reference/contact regions on In1 and In6. No required region conflicts with
another owner's region, an unrelated ground object, or foreign copper plus
clearance. This does not prove that connected, manufacturable quiet zones can
be filled while preserving all retained references.

Next construction and acceptance work:

- Connect the three local control-ground sets through owned quiet regions.
  Each region must contact its controller's pin-8 star; only that declared
  star may contact main ground. Preserve the four existing digital islands.
- Review the long surface returns before accepting the ground layout. The
  longest candidate return, R100 to U14, is 14.137 mm; consider short local
  quiet vias and owned copper instead of retaining this detour unchanged.
- Build and refill the zones, preserve the inlet/source copper and every
  retained native group, and check all new and retained adjacent references.
- Run native DRC, schematic parity and ERC; recapture actual connectivity;
  inspect current copper views before selecting a new revision.

Reproduce the candidate with `routing-search.py`, then run
`review-geometry.py` and `review-quiet-regions.py` from the repository root
using `.venv/bin/python`. The search reads the frozen plan-02 routes as its
starting point. Do not overwrite these bound reports after further changes;
create a new plan revision. None of these checks qualifies load, startup,
fault, thermal behavior, the accepted fabrication stack, or full installed fit.
