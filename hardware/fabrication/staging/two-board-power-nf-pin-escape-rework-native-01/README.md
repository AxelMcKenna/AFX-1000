# TBP60 NF pin-escape rework candidate

Three trapped surface-pad escapes are resolved, and both ABS_AUX_READY and
N19_F_WD_ARM are now connected. Power-board opens fall from 2,126 at
[TBP59](../two-board-power-nf-logic-detours-native-02/README.md) to **2,124**.
Open the [KiCad project](power_protection.kicad_pro).

The rework replaces thirteen declared front-layer segments on
N19_ARM_CONDITIONED, NF_NOT_OUTPUT_VALID and N12_STAGE_ENABLED. Thirty-five
new 0.20 mm segments and ten conventional 0.60/0.30 mm vias preserve those
networks and route the freed N_U35.11, N_U48.12 and N_U51.13 pads. Front/In2
routing shares the existing In1 ground reference. The existing arm-condition
via and its bottom-layer connection remain in place.

The [native checks](review.json) report zero geometry or schematic-parity
findings, zero ERC errors and two retained ERC warnings. The
[independent audit](nf-pin-escape-review.json) verifies exactly two intended
connection-group merges after the declared track removals, preservation of
all other retained connections, 2,038 retained ground-reference checks, and
continuous full-width reference coverage for all sixteen new path sections.
All eleven supply-plane fills and seven quiet-ground networks remain unchanged.

Only two ground zones are refilled. All 45 other authored fills retain their
original copper exactly. The [refill record](../two-board-power-nf-pin-escape-rework-filled-02/local-plane-fill.json)
bounds the same approximately 1.16 nm native supply-zone rounding difference
seen in TBP58/TBP59; the rounded supply fill is not substituted.

Six native copper detail views were [visually inspected](visual-review.json).
The [remaining NF survey](../two-board-nf-logic-reference-survey-04/survey.json)
records 41 missing joins across 37 selected open NF logic nets. All 94 surveyed
pad centers have ground coverage; this alone does not establish routable
escapes or complete return paths.

The [accepted routing plan](../two-board-nf-pin-escape-rework-plan-08/plan.json)
uses a polygon-corridor fallback to find passages missed by the regular grid,
with every proposed segment passing the same exact copper/reference screen.
Broader via-site enumeration allows both new control connections to coexist.
Earlier plans are diagnostics and were not authored into this candidate.

**Not ready for fabrication.** The signal board still has 251 opens. Complete
routing, AUX distribution, the approved codec footprint, power/startup/thermal
qualification, installed housing fit, accepted manufacturing stackup, final
BOM and reviewed manufacturing outputs remain unfinished. These layout checks
do not establish functional timing, EMC or thermal performance. The selected
public documentation remains TBP50; this working candidate is not released.
