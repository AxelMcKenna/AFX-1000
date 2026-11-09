# TBP54 startup reset routing candidate

This checked working candidate closes two startup reset connections after the
[TBP53 pin-access repair](../two-board-power-startup-access-native-02/README.md).
Power-board opens fall from 2,167 to **2,165**. Open the
[KiCad project](power_protection.kicad_pro).

Three 0.2 mm bottom-layer segments join E_U23 pins 3 and 4 on PWR_E28_RESET,
and E_U22.5 to E_U23.6 on E28_RESET_OUT. No vias are added. Existing copper,
component placement, zone outlines, schematic nets, and all 47 native filled
zones remain unchanged.

[Native checks](review.json) report zero geometry/parity/ERC errors and the two
retained isolated-reference ERC warnings. The [independent audit](startup-control-review.json)
verifies exactly the two declared connection-group merges, every other original
connection, **1,660 retained reference checks**, and full-width In6 ground
coverage beneath both new paths. All eleven supply planes and seven quiet-ground
networks are preserved. The new [bottom routes](plots/startup-reset-back.png) and
[In6 reference](plots/startup-reset-inner6.png) were [visually inspected](visual-review.json).

The [updated startup inventory](../two-board-startup-connectivity-survey-09/inventory.json)
records **51 missing joins across 29 open nets**. The
[access survey](../two-board-startup-reference-access-03/survey.json) finds ten
remaining uncovered pad centers among 73 selected still-open logic pads.
Supply and ground work are additional to the startup join count.

**Not ready for fabrication.** The signal board retains 251 opens and lacks
the approved ESS codec footprint. AUX distribution, load/startup/thermal
qualification, complete housing fit, accepted stackup, final BOM and reviewed
manufacturing outputs remain unfinished. No manufacturing release or order is
authorized by these layout checks. The selected public documentation still
describes [TBP50](../two-board-fabrication-status-50/status.json); this folder
records the newer checked working design.
