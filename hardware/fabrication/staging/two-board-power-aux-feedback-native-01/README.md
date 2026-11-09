# TBP51 AUX feedback BOM and land candidate

This working revision adds exact manufacturer part numbers for the three AUX
feedback resistors and manufacturer-recommended lands for P_R108/P_R109.
Nominal resistance and circuit connectivity remain unchanged. P_R108's value
label now correctly specifies the chosen part's 25 ppm/K temperature coefficient.

Open the [KiCad project](power_protection.kicad_pro). The
[part selection and BOM](../../parts/aux-feedback-01/README.md) explain the
voltage calculation, sources and remaining qualification work.

The [native check](review.json) reports 2,172 opens, zero geometry/parity errors
and two retained isolated-reference ERC warnings. The
[independent delta review](aux-feedback-review.json) checks all component and
circuit changes, native connectivity groups, retained reference coverage and
local fill scope. Tracks, vias, placements and zone outlines are preserved.

Four regulator-cell views were visually inspected:
[front](plots/aux-feedback-cell-front.png),
[back](plots/aux-feedback-cell-back.png),
[In1](plots/aux-feedback-cell-inner1.png) and
[In6](plots/aux-feedback-cell-inner6.png).
They show the new rectangular resistor lands and retained local routing and
return fields. Native SVG exports of all eight copper layers are in `plots/`.
The earlier `aux-feedback-*` crop was offset and is not the component review view.

**Not ready for fabrication.** This candidate does not replace the selected
[TBP50 checkpoint](../two-board-fabrication-status-50/status.json) yet. Exact-part
selection is not complete installed qualification: P_R130's current full
datasheet/land review, resistor lifetime and assembly limits, AUX load/startup
and thermal checks remain open. The two-board design also retains 251 signal
opens, the missing approved ESS codec footprint, incomplete housing fit,
provisional stackup and unfinished manufacturing outputs.
