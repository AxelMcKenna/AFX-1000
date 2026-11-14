# TBP63 POWER_READY connector ground returns

This candidate closes **one ground connection**, reducing power-board opens
from 2,095 at [TBP62](../two-board-power-control-return-planes-native-01/README.md)
to **2,094**. It also repairs three of the seven remaining control-trace
reference gaps. Open the [KiCad project](power_protection.kicad_pro).

The [plan](../two-board-ready-return-planes-plan-01/plan.json) extends existing
In4 and In6 main-ground planes beneath the POWER_READY connector routing.
P_J22 pin 2 now joins main ground. The existing ground via beside the signal's
layer transition and that connector pin contact both extended reference planes.
No components, tracks, vias, drill holes, board outlines or schematic connections
change. Only two ground-zone outlines and their fills change.

The [native report](review.json) records zero geometry/parity findings, zero
ERC errors and two retained ERC warnings. The [independent audit](ready-return-planes-review.json)
proves the single declared ground-group merge, preservation of every other
native group, all original objects, and 2,279 retained reference checks.
All eleven supply planes and seven quiet-ground networks remain unchanged.

All 45 retained zone fills preserve their original copper exactly. The
[fill record](../two-board-power-ready-return-planes-filled-02/local-plane-fill.json)
documents the recurring approximately 1.16 nm native rounding difference in one
supply zone; the rounded supply copper is not substituted for the original.

Four native layer views were inspected in the
[connector detail](plots/ready-connector-inspection.png), with hashes and
observations in the [visual review](visual-review.json).
The [gap comparison](ready-return-improvement-review.json) proves three
POWER_READY sections now have full adjacent-ground reference coverage and no
existing gap worsens. The [whole-net survey](../two-board-control-return-survey-after-04/survey.json)
retains four strict reference gaps and zero new gaps across the seventeen
control nets previously touched by TBP61.

The four remaining gaps occur at plated connector-pad clearances: two
POWER_READY branches at P_J22, N19_ARM_CONDITIONED at N_J1 pin 18, and
PWR_NF_OUTPUT_VALID at N_J1 pin 30. Their overlap with those clearances is
recorded as diagnostic evidence only. It does not waive the strict reference
check or qualify connector return transitions. POWER_READY also still has an
unjoined signal group; added reference coverage does not complete that net.

**Not ready for fabrication.** The signal board has 251 opens and the power
board has 2,094. Complete routing and returns, AUX distribution, an approved
codec footprint, power/startup/thermal qualification, complete assembly fit,
an accepted stackup, final BOM and manufacturing outputs remain unfinished.
The CAD package remains an unpowered fit prototype. This copper-only change
preserves board and component mounting geometry. The selected public checkpoint
remains TBP50; TBP63 is a verified working candidate.
