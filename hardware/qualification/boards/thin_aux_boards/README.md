# TA01 auxiliary-board thickness candidates

The editable candidates in [generated](generated/) use 1.2 mm nominal finished
PCB thickness with a proposed 1.08–1.32 mm receiving range. The parent NF and FPC
boards and all sealed records remain unchanged. Footprint positions, copper XY
geometry, holes, keepouts and outlines are retained. The FPC central dielectric
changes from 1.06 to 0.66 mm; the NF still requires a supplier-defined six-layer
stackup.

The [strict native review](generated/native-complete-review.json) records:

| Candidate | ERC findings | DRC violations / parity | Open connections |
| --- | --- | --- | --- |
| FPC, four layers | 0 | 0 / 0 | 0 |
| NF, six layers | 2 ground-reference warnings | 0 / 0 | 204 |

All native rule categories are enabled, pin/value comparisons match, and native
KiCad confirms 1.2 mm thickness. Checks run in the pinned Linux container with
zero Mac CAD launches. These checks do not qualify a manufactured board.

The NF warnings are retained in the raw ERC report: ISO7721 U19.4 and U24.4 are
named GND1 and connect to the local negative-domain references N19_P03_SRC and
N12_P03_SRC. The host-side GND2 pins connect to AGND. Review these as isolated
domains; connecting GND1 to AGND would change the circuit. The first packaging
check also found a missing external symbol-library dependency. Its explicit
[capture receipt](generated/symbol-dependency-capture.json) and the corrected
review preserve that history.

For the parent PH connector's 0.8–1.6 mm applicable range, 1.08/0.8 = 1.35 and
1.6/1.32 = 1.212. The proposed finished-thickness limits therefore meet a 1.2
guard at both ends. A manufacturing quote must confirm those finished limits,
including coatings; catalog capability is not an accepted job-specific stackup.

The [edge-shim drawing](generated/edge-shims.scad) is a receiving proposal for
eight 6 × 1.2 mm edge pieces, nominally 0.4 mm thick. A finished installed shim
range of 0.36–0.44 mm combines with the PCB range to reproduce the old numerical
1.44–1.76 mm stack. This has not established shim retention, material grade,
compression, adhesive allowance or assembly fit. Any adhesive must fit inside
the installed shim thickness requirement.

Thinner boards have approximately 0.422 of the original bending stiffness at
equal material properties. Deflection, vibration and mounting checks must be
refreshed. Rear component datums and measured lead trimming also need new
receiving geometry; untrimmed manufacturer lead endpoints do not shorten
automatically. No old enclosure qualification is inherited.

Neither candidate is released for fabrication. The NF remains unrouted;
current/thermal/fault limits, complete assembly receiving, manufacturing
acceptance and physical measurements remain open for both candidates.
