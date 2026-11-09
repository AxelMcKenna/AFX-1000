# TBP41 startup logic checkpoint

**Development checkpoint; not ready for fabrication.** Native checks report
**2,294 open power-board connections**, zero geometry/parity/ERC errors and
two retained isolated-reference ERC warnings. The signal board remains at
251 opens with its ESS codec footprint missing.

U29 and U40 move with their existing 100 nF bypass capacitors. Their part
values, packages and pin nets are unchanged. The previous U29 supply pin was
blocked by neighboring traces; the revised placement reserves an escape for
every pin before interconnecting the cells. U29 pin 1 (ALL_RAILS_ALLOW) remains
unrouted; its unused reserved track/via is not emitted.

| Component | Side | Center (mm) | Orientation |
| --- | --- | --- | --- |
| E_U29 | Bottom | 140.0, 139.0 | 90° |
| E_C74 | Bottom | 142.1, 134.2 | 90° |
| E_U40 | Front | 133.0, 156.5 | 270° |
| E_C83 | Front | 135.1, 161.3 | 270° |

This pass restores both U29 master-enable pins to their prior group and adds
the three U40 PG inputs, three Schmitt outputs, U29 FOLLOW1 output, AUX_VALID
input, two AUX supply branches, two local bypass supply connections and four
main-return connections. Exactly **16 previously open connections close**.
The U29/U40 AUX branches connect to the existing AUX supply group; full-unit
AUX loading, startup and transient qualification remain unfinished.

83 tracks and 22 vias are added; two old U29 terminal tracks are retired.
The board now has 2,683 tracks, 338 vias, 36 zones and 3,032 native connection
groups. All 1,086 electrical parts, 3,420 schematic pin entries and 1,101 total
footprints are retained. Mechanical screens cover the four moved parts against
the existing provisional body, tail, courtyard and height reserves; they do
not establish complete installed housing fit.

The first native candidate was rejected: although it had zero geometry/parity
errors, In6 routes split U17's quiet return and disconnected C47 and R112.
The corrected plan moves FOLLOW1, PG0 and PG2 transitions onto existing bottom
copper before entering In2/In3, preserving all four quiet fields and their
single-star connections. Ordinary net DRC alone would not prove this.

The independent [connection and geometry audit](startup-logic-review.json)
checks exact undeclared board trees, four rigid footprint moves, every new
track/via, exactly sixteen native group merges, all prior connectivity,
quiet-return ownership, 299 prior complete adjacent-ground projections and
22 own-field ILM/DVDT reference sections. New-via drill-to-SMD copper is at
least 0.240001 mm; minimum hole spacing is
0.700000 mm. No clearance rule is waived.

One In5 main-return outline extends to the logic cells; seven zones are
refilled and 29 retained fills compare exactly. The In4 digital-source field
keeps one 836.210216 mm² fill and all 20 prior contacts. Its uncovered In5
projection remains 0.355273 mm². All 33 fast-OV route sections retain their
adjacent-ground coverage. This is geometry evidence, not current/thermal proof.

**New logic reference routing remains substantially incomplete: only 2/32
non-ground sections have complete adjacent-ground coverage.** Retained support
coverage remains 24/28; retained TBP40 startup sections are 6/15 after retiring
the old U29 tie. See the [retained reference review](startup-logic-reference-review.json).
Next work must complete those references, U29 ALL_RAILS_ALLOW, U30/U34/U41
supplies and bypass, remaining PG/enable paths and pull-up AUX ends before
claiming a complete startup chain. Protected outputs, remaining supply/return
and signal routing, ESS inputs, accepted stack, exact BOM, installed fit,
reviewed manufacturing outputs and prototype bring-up plan remain required.

## Native views

[Front](plots/front.png) · [Bottom](plots/back.png) · [Inner overview](plots/inner-contact-sheet.png)

[Logic front](plots/logic-front.png) · [Logic bottom](plots/logic-back.png) ·
[In1](plots/logic-inner1.png) · [In2](plots/logic-inner2.png) ·
[In3](plots/logic-inner3.png) · [In4](plots/logic-inner4.png) ·
[In5](plots/logic-inner5.png) · [In6](plots/logic-inner6.png)

All eleven views were directly inspected. The native SVGs and render bindings
remain alongside the PNGs. [Construction plan](../two-board-startup-logic-plan-02/README.md)
and [native results](review.json) record the exact candidate.
