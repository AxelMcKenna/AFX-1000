# TBP64 fan watchdog fast connection

This candidate completes **WD_OK_FAST**, joining F_U6 pin 3 to the existing
F_U5 pin 4 / F_U12 pin 2 group. Power-board opens fall from 2,094 at
[TBP63](../two-board-power-ready-return-planes-native-01/README.md) to **2,093**.
Open the [KiCad project](power_protection.kicad_pro).

The [broader control plan](../two-board-control-corridor-plan-03/plan.json)
examined 82 open control nets with 118 missing joins. It found one screened
connection and deferred 102 candidate group pairs. This is not a complete
routing solution for the remaining control nets.

The added route is 49.434 mm long: two short front escapes and an In2 bridge,
using four 0.20 mm tracks and two 0.60/0.30 mm vias. All three paths use the
same In1 main-ground reference. No original components, tracks, vias, drill
holes, board outlines, zone outlines or schematic connections change.

[Native checks](review.json) report zero geometry/parity/ERC errors and two
retained ERC warnings. The [independent audit](control-corridor-review.json)
verifies exactly one declared group merge, all other native groups unchanged,
2,284 retained reference checks, three new referenced paths and both declared
same-reference transitions. All eleven supply fields and seven quiet-ground
fields remain unchanged. Three main-ground zones refill; the other 44 fills
remain byte-exact in the authored board. The
[fill record](../two-board-power-watchdog-fast-filled-02/local-plane-fill.json)
retains original supply copper despite the recurring bounded native rounding
difference in one supply zone.

The [whole-net survey](../two-board-watchdog-fast-return-survey-01/survey.json)
checks all ten WD_OK_FAST tracks and finds no uncovered reference sections.
Three native views were inspected in the
[watchdog detail](plots/watchdog-fast-inspection.png); hashes and observations
are recorded in the [visual review](visual-review.json).

**Not ready for fabrication.** The signal board still has 251 opens; the power
board has 2,093. The four TBP63 connector-end reference gaps remain separate
work. Full routing, AUX distribution, approved codec footprint, loaded startup
and fault behavior, thermal qualification, complete assembly fit, accepted
stackup, final BOM and manufacturing outputs remain unfinished. The housing is
an unpowered fit prototype; board and component mounting geometry is unchanged.
