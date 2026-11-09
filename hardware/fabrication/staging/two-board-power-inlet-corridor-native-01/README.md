# Inlet corridor — first geometry candidate

This candidate closes nine connections relative to TBP32, leaving **2,374
power-board opens**. It is not selected for fabrication. The second inlet
candidate widens the inner copper at mounting holes; the first remains
evidence of the original geometry and its review.

Two internal DC feed planes connect I_F1.2 to the Q101 input bank through
12 inlet vias and five source vias (four new, one retained). Two internal
AGND planes connect I_J1.2 to the protection-cell return. Native ground
connectivity also joins U20 and six formerly isolated ground terminals;
the exact nine merged groups are enumerated in the independent report.
This is not qualification of whole-unit ground-current distribution.

Native geometry/parity/ERC errors are zero; the two isolated-reference
warnings remain. All 3,121 earlier native connection groups, 1,101 complete
footprints, pin assignments, values and packages are preserved. The board
has 2,444 tracks, 250 vias and 19 zones. Eleven earlier fills remain exact.
The expanded front source plane contacts all three Q101 source lands and
all five source transition vias. The input TVS and both G_NT1 pads remain
isolated and must still be connected appropriately.

All 33 fast-OV route sections retain adjacent ground-reference coverage.
The AUX ground group and its local copper remain unchanged and separate
from U101's return. Every new filled piece contacts its intended native
group; In5 includes a separate 26.73 mm² region attached through a ground
via, so the 19 zones do not mean 19 contiguous pieces. All 250 via drills
pass the SMD-land check, with minimum gap 0.165067 mm.

The four internal corridors each narrow to two 0.58 mm strips at H_NEW2.
This follows from applying a surface screw-head reserve to internal copper.
The [revised clearance rationale](../../parts/inlet-jumper-01/INTERNAL-MOUNT-COPPER.md)
separates internal hole clearance from surface fastener clearance. No
current-capacity, sharing, temperature-rise or final stack approval follows
from the native connectivity/clearance pass.

[Native checks](review.json) · [Independent review](inlet-corridor-review.json)
· [Construction](inlet-corridor-routing.json)
· [Native capture](../two-board-power-routing-inputs-2374-inlet-corridor-01/capture.json)
· [Filled-zone provenance](../two-board-power-inlet-corridor-filled-01/local-plane-fill.json)
· [Inner copper overview](plots/inner-contact-sheet.png)
· [Source-cell front](plots/local-front.png)
· [Source-cell In5](plots/local-inner5.png)

Further work includes the TVS connection, current/thermal/transient review,
remaining power and signal routing, accepted stack and BOM, approved ESS
footprint inputs, manufacturing outputs and full installed housing fit.
Signal main still has 251 opens. Nothing is ordered or released.
