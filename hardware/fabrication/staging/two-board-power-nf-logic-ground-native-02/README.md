# TBP58 NF reference coverage and ground candidate

This checked working candidate closes fourteen ground connections after
[TBP57](../two-board-power-nf-logic-detours-native-01/README.md), reducing
power-board opens from 2,144 to **2,130**. Open the
[KiCad project](power_protection.kicad_pro).

The In1 and In6 main-ground outlines extend across the remaining NF logic
area. Ten short ground-pad tracks and 42 conventional vias connect local
grounds and stitch the reference planes. Native connectivity confirms the
ten pad joins plus four existing ground groups: N_U28/N_C67, the P_U102 AUX
regulator ground group, P_J2.2 and P_J104.3. This does not qualify their
installed current paths or the AUX regulator's thermal performance.

The [independent audit](nf-logic-ground-review.json) verifies all fourteen
ground-group merges, preservation of every other original connection,
1,954 retained reference checks and all ten new ground paths. All 42 added
vias touch both extended main-ground planes. The seven quiet-ground networks
retain their exact contacts and sole main-ground star returns. All eleven
supply-plane fills remain exactly unchanged. Five ground zones are refilled;
42 other fills retain their original copper.

The [updated reference survey](../two-board-nf-logic-reference-survey-02/survey.json)
finds **zero uncovered centers among 118 pads** in the selected remaining NF
logic nets, down from 26. This is pad-center coverage, not a guarantee that
every escape or route is clear. These nets still need 47 signal joins.

[Native checks](review.json) report zero geometry/parity/ERC errors and two
retained ERC warnings. Twelve native copper views were
[visually inspected](visual-review.json). A strict initial refill comparison
stopped on a roughly 1.16 nm supply-polygon difference; the
[retained-fill procedure](../two-board-power-nf-logic-ground-filled-03/local-plane-fill.json)
keeps the original supply copper exactly, copying only the declared ground
fills. The independent audit checks that preservation and the numerical bound.

**Not ready for fabrication.** The signal board retains 251 opens. Complete
routing, the approved codec footprint, AUX distribution, power/startup/thermal
qualification, installed housing fit, accepted stackup, final BOM and reviewed
manufacturing outputs remain unfinished. The selected public documentation
still describes TBP50; this working candidate is not a manufacturing release.
