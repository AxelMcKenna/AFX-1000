# Power/protection TBP40 — startup fanout checkpoint

**Not ready for fabrication.** This is the current partial-routing checkpoint,
with **2,310 power-board open connections**. The signal board remains at
251 opens with its ESS codec footprint missing. The complete startup chain,
protected outputs, supply/return distribution and full installed housing fit
are unfinished. Daisy Seed 3 remains on the separate signal main board.

## Changes

Four eFuse supply-good pins now reach their 10 kΩ pull-up resistors; three
follower-enable pins reach their 47 kΩ pull-downs and each pull-down reaches
its own device's quiet return. This closes **ten native connections**. Seven
resistors move on the bottom side; packages, values and pin nets are unchanged.
The pull-up AUX supply ends, Schmitt receivers and gated follower drivers still
need routing, bypass and reference review.

| Resistor | Local connection | Bottom trace length |
| --- | --- | --- |
| E_R103 | E_U15 supply good | 13.429 mm |
| E_R107 | E_U16 supply good | 10.261 mm |
| E_R111 | E_U17 supply good | 12.663 mm |
| E_R119 | E_U33 supply good | 1.505 mm |
| E_R108 | E_U16 enable / quiet return | 1.985 / 3.166 mm |
| E_R112 | E_U17 enable / local quiet via | 7.840 / 1.077 mm |
| E_R120 | E_U33 enable / quiet return | 5.662 / 0.880 mm |

The eight OVLO/RCBCTRL ground escapes are replanned to free PG/EN routes.
E_U17's star via moves 0.25 mm; E_C47's bottom return shortens from 9.031 mm
to 1.600 mm using a local quiet via. E_R112 receives a separate local quiet
via. Both reach only U17's In6 quiet field; all four cells retain a single
connection to main return through their own GND8 star. A redundant master-enable
detour is shortened, and its upper bottom trace shifts 0.5 mm to free space.
The complete earlier master-enable connection group is preserved.

The final candidate adds 62 tracks and 18 vias while retiring 27 tracks and
10 vias. Totals are **2,602 tracks, 316 vias and 36 filled zones**. Eleven zone
outlines change; 15 zones are refilled and 21 retained fills match exactly.
About 4.658 mm² of authored In5 return copper is restored where retired vias
left clearance holes. The first native fill exposed an In4 integer-grid
rounding difference; that unchanged outline is now explicitly refilled.
An intermediate restoration trial enlarged unrelated hole reserves and was
rejected before native validation; it is not the selected board.

## Verification and limits

Native geometry and schematic-parity findings are zero. ERC has zero errors
and the same two isolated-reference warnings. All 1,086 electrical parts,
1,101 footprints, 3,420 schematic pin entries and 3,481 mapped pads remain.
Independent comparison verifies exactly the ten intended joins, all other
connection groups, all undeclared board objects and the seven rigid footprint
moves. There are 3,048 current native connection groups and 6,639 captured
physical objects. Fifty-five older generated pad identities are matched only
by unique complete physical/net data.

All 274 complete adjacent-ground projections present in TBP39 are retained,
along with all 33 fast-overvoltage route sections. The 22 critical ILM/DVDT
sections retain their own quiet references, including two earlier tiny via-edge
gaps. The broader retained-support screen remains 24/28 complete. Only
**7/16 new startup route sections** have complete adjacent-ground projection;
reference routing and timing/noise qualification remain unfinished.

The In4 source plane retains all 20 contacts and one
838.584705 mm² fill. Its In5 reference screen leaves
0.355273 mm² uncovered, compared with 2.462734 mm² before restoring
the retired-via holes. This projection is not a current or thermal rating.
The TBP35 inlet-resistance model does not model these later copper changes.

For the new vias, the minimum drill-to-SMD copper gap is
0.166926 mm and minimum hole-to-hole gap is
0.515648 mm. The minimum screened spacing to other
surface quiet-ground ownership is 0.212646 mm.
The seven passive moves pass the existing body, courtyard and preliminary
housing-height screen; complete fastener, support, cable, cooling and tolerance
fit is still unverified. The eight-layer stack remains provisional.

## Evidence and views

- [Native checks](review.json), [independent connection/quiet-ground audit](digital-startup-review.json), [current reference screens](digital-startup-reference-review.json).
- [Construction and exact object changes](digital-startup-routing.json), [planning inputs](../two-board-digital-startup-plan-01/README.md), [native capture](../two-board-power-routing-inputs-2310-digital-startup-02/capture.json).
- [Front](plots/front.png), [bottom](plots/back.png), [six inner layers](plots/inner-contact-sheet.png).
- [Startup front](plots/startup-front.png), [startup bottom](plots/startup-back.png), [In1](plots/startup-inner1.png), [In4](plots/startup-inner4.png), [In5](plots/startup-inner5.png), [In6](plots/startup-inner6.png), [visual review](plots/visual-review.json).
- [Selected two-board status](../two-board-fabrication-status-40/status.json).

Next: finish the Schmitt/gated startup chain, pull-up supplies, local bypass
and PG/EN references; complete protected outputs and remaining distribution;
resolve ESS package inputs, actual load and fault limits, accepted stack, exact
BOM, installed fit, manufacturing outputs and the prototype bring-up plan.
No fabrication order or release is authorized by these partial checks.
