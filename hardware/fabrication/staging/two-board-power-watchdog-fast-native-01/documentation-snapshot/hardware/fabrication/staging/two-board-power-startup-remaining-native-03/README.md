# Power/protection startup-cell completion checkpoint

This revision closes **27 connections**, reducing power-board opens from
2,199 to **2,172**. It is not ready for fabrication.

U18/U19/U20/U22/U23/U24/U26/U27 gain their local bypass and both IC/capacitor
ground returns. Together with U21/U25/U28, **all eleven U18–U28 local cells
are now connected**. U19 gains its additional AUX pin tie, and U22's two
additional grounded inputs reach main ground. **None of these eleven ICs is
yet connected to the auxiliary regulator output.** Startup operation remains
unverified.

Five capacitors move: C57, C59, C67, C71 and C72. No ICs, component values or
schematic pin nets change. The pass adds 69 tracks and 20 vias, retires 112
tracks, replaces U20's enable routing with a front-layer bridge and reroutes
six In6 signal spans to preserve adjacent references. One main In6 ground
outline extends near U26. Four main-ground zones are refilled; the other
43 fills and all other authored zone outlines remain exact.

## Checks and evidence

- [Native review](review.json): zero geometry/parity errors. Independent
  [connectivity review](startup-cell-review.json) confirms zero ERC errors,
  two retained isolated-reference warnings, all 27 intended merges and every
  other native connection group and physical object preserved.
- [Reference review](startup-cell-reference-review.json): all **1,555 retained
  reference cases**, 18 new non-ground paths and nine previous startup-repair
  paths pass. All eleven supply-plane fields and seven quiet-ground fields
  remain exact. All seven quiet networks preserve connected ownership and
  pin-8-only main returns. The existing unanchored ground fragment is excluded
  from usable reference copper and remains exactly unchanged.
- Earlier candidates lost reference coverage on three AUX reset tracks. The
  selected timeout detour includes additional space for native plane minimum
  thickness. The current review explicitly verifies all three repaired gaps
  against the rejected candidate, without relaxing audit tolerances.
- [Routing manifest](startup-cell-routing.json) and
  [plan](../two-board-startup-remaining-plan-06/plan.json) record exact edits.
  Pending flags in earlier stage reports describe those stages; the later
  native, connectivity and reference reports record completed checks.
- [Visual review](plots/visual-review.json): 13 directly inspected views with
  no additional findings. This is copper inspection, not electrical or
  manufacturing qualification.

Current counts: 1,101 footprints, 1,086 electrical parts, 3,420 schematic pin
entries, 3,481 mapped pads, 3,012 tracks, 482 vias, 47 zones, 7,215 captured
objects and 2,910 native connection groups. Open the
[KiCad project](power_protection.kicad_pro) to inspect the editable design.

## Current copper

[![Current bottom copper](plots/back.png)](plots/back.svg)

[Front copper](plots/front.png) · [Six inner layers](plots/inner-contact-sheet.png)
· [West back detail](plots/west-startup-back.png)
· [West front detail](plots/west-startup-front.png)
· [East back detail](plots/east-startup-back.png)
· [East ground and signal detours](plots/east-startup-inner6.png)

## Remaining work

The [startup-net survey](../two-board-startup-connectivity-survey-06/README.md)
records **58 missing joins across 32 of 91 surveyed nets**. The separate
[cell survey](../two-board-startup-cell-survey-04/README.md) confirms local
bypass/ground completion and missing source connectivity for U18–U28.
The [AUX inventory](../two-board-aux-distribution-survey-02/README.md) records
81 IC supply pins: eight connected to the regulator and 73 unconnected, with
28.5 µF nominal direct capacitance. Actual current, effective capacitance,
startup ramp and installed thermal limits must be reconciled before accepting
AUX source distribution. Sense/timing placement and startup/fault behavior
also remain unverified.

Protected outputs, analog/module distribution, source/input loops, force/quiet
returns and signal routing remain unfinished. The signal board retains 251
opens and lacks an approved ESS codec footprint. Whole-unit electrical and
thermal checks, complete installed housing fit, accepted stack/plating, exact
BOM, manufacturing outputs and prototype bring-up are still required.
Historical TBP35 inlet resistance results do not qualify current copper.
No fabrication release or order is made by this checkpoint.
