# TBP61 broader control-routing candidate

This pass completes **24 joins across 17 control nets**, reducing power-board
opens from 2,124 at [TBP60](../two-board-power-nf-pin-escape-rework-native-01/README.md)
to **2,100**. Eight of the touched nets are now physically complete.
Open the [KiCad project](power_protection.kicad_pro).

The batch adds 199 segments at 0.20 mm width and 23 conventional 0.60/0.30 mm
vias. Forty-seven route sections use front copper and In2, sharing the In1
main-ground reference. Existing inner contacts are reused where possible.
All original tracks, vias, component placements, board geometry and schematic
connections remain unchanged. The [screened plan](../two-board-control-corridor-plan-02/plan.json)
retains every intended join from the broader 90-net control selection.

The [native checks](review.json) report zero geometry/parity findings, zero ERC
errors and two retained ERC warnings. The [independent audit](control-corridor-review.json)
verifies exactly the 24 declared native group merges, preservation of all other
connections, 2,072 retained reference checks and full-width ground-reference
coverage for all 47 new path sections. All eleven supply-plane fills and all
seven quiet-ground networks remain unchanged.

The first trial passed ordinary DRC but failed two new reference checks.
Both local paths were rerouted against the actual refilled ground without
dropping any joins or moving vias. Only this revised candidate passes the
independent reference audit. Eleven [native copper views](visual-review.json)
were visually inspected, including a larger detail of the corrected escapes.

Four ground zones are refilled. All 43 other fills retain their original copper
exactly. The [refill record](../two-board-power-control-corridors-filled-04/local-plane-fill.json)
bounds the recurring approximately 1.16 nm native supply-zone rounding
difference; the original supply copper is retained.

## Remaining whole-net reference work

A [full touched-net survey](../two-board-control-return-survey-after-02/survey.json)
checks existing as well as added tracks. Thirteen pre-existing trace sections
still lack complete adjacent main-ground coverage: four on WD_OK, one on
N19_ARM_CONDITIONED, seven on POWER_READY and one on PWR_NF_OUTPUT_VALID.
The [before/after comparison](retained-partial-reference-review.json) verifies
that none of those uncovered areas worsened by more than 1e-6 mm². There are
**zero new unreferenced track sections**. These remaining gaps, layer-transition
returns and loaded timing still require qualification before fabrication.

The narrower [NF selection survey](../two-board-nf-logic-reference-survey-05/survey.json)
now records 36 missing joins across 33 selected open nets. All 85 surveyed pad
centers have ground coverage; center coverage alone is not a complete route or
return-path proof.

**Not ready for fabrication.** The signal board retains 251 opens. Complete
routing and returns, AUX distribution, approved codec footprint, power/startup/
thermal qualification, installed housing fit, accepted stackup, final BOM and
reviewed manufacturing outputs remain unfinished. The selected public
README/checkpoint remains TBP50; this working candidate is not a fab release.
