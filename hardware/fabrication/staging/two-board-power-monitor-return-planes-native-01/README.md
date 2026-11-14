# TBP67 monitor logic ground returns

This verified working candidate closes **five ground connections**, including
the four remaining surveyed SN74 monitor-logic ground pins. Power-board opens
fall from 2,042 to **2,037**. All 75 surveyed SN74 GND pins now reach the main
ground group. Open [power_protection.kicad_pro](power_protection.kicad_pro).

Four short surface tracks and fifteen ground vias connect the monitor cells
and stitch extended In1/In6 reference fields along the actual left and upper
arms of the C-shaped board. Components, board outline, schematic nets and
existing tracks/vias are preserved. The [housing comparison](housing-compatibility.json)
confirms all 1,101 footprint records, board general settings and Edge.Cuts
still match the sealed r6 housing's TBP61 basis.

[Native checks](review.json) report zero geometry/parity errors and two retained
ERC warnings. The [independent audit](monitor-return-planes-review.json)
checks all five group merges, every retained object and connection group,
2,401 existing reference cases, four new paths, fifteen both-plane stitches
and all seven quiet-ground networks. The [control survey](../two-board-control-return-survey-after-08/survey.json)
retains four older connector-end gaps and finds no new gaps.

Nine supply fields remain exact. The two DC-input sheets each lose
11.128765 mm² around the declared ground vias, including local cleanup at the
native 0.25 mm minimum copper width. Remote rounding changes are bounded to
2 nm and less than 1e-6 mm². Both sheets remain connected and their contact
banks are preserved. The [sheet comparison](../two-board-monitor-inlet-via-comparison-01/review.json)
estimates a **0.6246%** paired resistance increase on its finest unshifted grid;
refinement and grid-shift differences remain below 2%. This does not establish
current capacity, actual peak current density, temperature rise or a complete
input-loop rating. Via barrels and installed load/thermal behavior are excluded.

Nine native layer details were [visually inspected](plots/visual-review.json).
[Final verification](final-review.json) binds the native, topology, reference,
supply-comparison and visual records. A native refill rounding difference was
diagnosed; 41 unaffected authored fills were retained exactly. Failed trial
outputs remain separate from this candidate.

**Not ready for fabrication.** The signal board still has 251 opens and a
missing approved ESS footprint. Remaining power routing, AUX distribution,
four connector-end reference gaps, loaded startup/fault behavior, exact parts,
accepted stackup, complete installed housing/harness/cooling and manufacturing
outputs remain unfinished. Connected logic grounds do not establish powered
or functioning logic.
