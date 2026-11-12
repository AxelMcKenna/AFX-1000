# TBP62 watchdog and power-ready ground returns

This candidate closes **five ground connections**, reducing power-board opens
from 2,100 at [TBP61](../two-board-power-control-corridors-native-02/README.md)
to **2,095**. It also repairs six of the thirteen previously identified
control-trace reference gaps. Open the [KiCad project](power_protection.kicad_pro).

The [plan](../two-board-control-return-planes-plan-01/plan.json) extends the
existing In1/In6 main-ground planes under the fan-watchdog and power-ready
cells. Four new 0.20 mm tracks connect F_U4 pins 4/9 and P_U26 pins 1/2 to
four local 0.60/0.30 mm ground vias. Ten additional vias connect the two
reference layers. The plane extension also connects the existing E_J3 pin 2
ground group. No components, board outlines, schematic connections, existing
tracks or existing vias move or change.

The [native report](review.json) has zero geometry/parity findings, zero ERC
errors and two retained ERC warnings. The [independent audit](control-return-planes-review.json)
verifies exactly five declared group merges, preservation of every other
native group, 2,270 retained reference checks, all four new ground paths,
and all fourteen vias contacting both extended planes. All eleven supply
planes and all seven quiet-ground networks remain unchanged.

Only two ground fills change. All 45 other fills retain their original copper
exactly. The [fill record](../two-board-power-control-return-planes-filled-02/local-plane-fill.json)
documents the recurring approximately 1.16 nm native rounding difference in
one supply zone; that rounded copper is not substituted for the original.

Eight native layer views were inspected in the
[watchdog detail](plots/watchdog-return-inspection.png) and
[power-ready detail](plots/ready-return-inspection.png). Their hashes and
observations are in the [visual review](visual-review.json).

## Remaining return-path work

The [comparison of all thirteen prior gaps](control-return-improvement-review.json)
proves that six now have full adjacent-ground coverage and none of the others
worsens. All four WD_OK gaps and two POWER_READY gaps are repaired. The
[whole-net survey](../two-board-control-return-survey-after-03/survey.json)
still records seven pre-existing gaps and zero new unreferenced track sections
across the seventeen control nets previously touched by TBP61.

Five remaining sections belong to POWER_READY near P_J22/P_R204 and its
In3 segment. Two short remaining gaps on N19_ARM_CONDITIONED and
PWR_NF_OUTPUT_VALID coincide with their own plated connector-pad clearance
regions. This overlap is recorded as diagnostic evidence only: it does not
waive the strict reference checks or qualify connector return transitions.
Nearby return connections, layer transitions and loaded timing remain work.

**Not ready for fabrication.** The signal board still has 251 opens, and the
power board has 2,095. Complete routing/returns, AUX distribution, approved
codec footprint, power/startup/thermal qualification, complete assembly fit,
accepted stackup, final BOM and manufacturing outputs remain unfinished.
The CAD package remains an unpowered fit prototype. This copper-only change
preserves its component and PCB mounting geometry, but establishes no thermal
or powered assembly qualification. The selected public checkpoint remains
TBP50; TBP62 is a verified working candidate.
