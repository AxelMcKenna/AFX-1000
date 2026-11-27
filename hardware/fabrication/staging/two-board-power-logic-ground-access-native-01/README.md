# TBP65 local logic-ground connections

This candidate connects **30 previously disconnected logic-IC GND pins** to
main ground. Power-board opens fall from 2,093 at
[TBP64](../two-board-power-watchdog-fast-native-01/README.md) to **2,063**.
Open the [KiCad project](power_protection.kicad_pro).

The [ground-access survey](../two-board-logic-ground-access-survey-02/survey.json)
selects SN74-family power-input pins explicitly named GND in the schematic.
It found 47 disconnected pins, including 32 with existing adjacent main-ground
coverage. The [plan](../two-board-logic-ground-access-plan-01/plan.json) connects
30 using local escapes and leaves 17 for further access/reference work.
It does not substitute ground copper beneath an SMD pad for a real connection.

The pass adds 36 tracks, 0.20 mm wide, and thirty 0.60/0.30 mm ground vias.
Every via contacts the existing main In1 and In6 fields. No component,
original track or via, board outline, zone outline or schematic net changes.
The four affected main-ground fills are renewed; all 43 other fills preserve
their original authored copper exactly. All eleven supply fields and seven
quiet-ground networks remain unchanged. The
[fill record](../two-board-power-logic-ground-access-filled-02/local-plane-fill.json)
keeps the original supply fill despite the recurring bounded native rounding
difference in one retained supply zone.

[Native checks](review.json) record zero geometry/parity/ERC errors and two
retained ERC warnings. The [independent audit](logic-ground-access-review.json)
verifies exactly thirty declared ground-group merges, every other native group
preserved, all 2,288 prior reference cases, all thirty new local ground paths,
all thirty via contacts, and the SN74 GND pin identity from the native netlist.
The [control-net survey](../two-board-control-return-survey-after-05/survey.json)
retains four connector-end reference gaps and no new gaps across the seventeen
control nets from TBP61.

Twelve native layer views were inspected in the
[western](plots/logic-west-inspection.png),
[middle](plots/logic-middle-inspection.png) and
[eastern](plots/logic-east-inspection.png) details.
Hashes and observations are recorded in the [visual review](visual-review.json).

**Not ready for fabrication.** The signal board still has 251 opens and a
missing approved ESS codec footprint; the power board has 2,063 opens. Remaining
logic grounds, signal routing, AUX distribution, supply and return sizing,
loaded startup/fault checks, thermal design, complete installed assembly,
accepted stackup, exact BOM and manufacturing outputs remain unfinished.
The housing remains an unpowered fit prototype. This pass changes copper only
and preserves its board/component mounting geometry.
