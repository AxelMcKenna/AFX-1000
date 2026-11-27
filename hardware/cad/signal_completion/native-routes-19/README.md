# Right output driver branch

The M_DRV_R branch joins A_R505 pin 2 on the top side to A_R507 pin 1 on the bottom side. Its two 0.20 mm traces total 7.67 mm. The transition uses a 0.60 mm via with a 0.30 mm drill.

KiCad confirms the full trace width has continuous adjacent ground outside the via clearance. A nearby grounded via contacts both reference layers. The new bottom trace uses an In6.Cu analog-ground pour. The only pre-existing zone layer that changes is In1.Cu, where the signal via clears the ground plane.

Native refill confirms the intended pad-group join and 118 remaining opens. Geometry DRC and ERC pass. Schematic parity still reports the missing A_U201 footprint. Loaded audio performance remains unverified.

[Trace and reference geometry](reference-review.json) · [Connectivity](native-review.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
