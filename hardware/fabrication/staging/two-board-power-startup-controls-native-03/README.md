# TBP52 startup-control routing candidate

This working candidate closes five startup-control connections relative to
[TBP51](../two-board-power-aux-feedback-native-01/README.md), reducing power-board
opens from 2,172 to **2,167**. Open the [KiCad project](power_protection.kicad_pro).

The added connections are the U19 AUX-reset pull-up, the U21–U25 armed latch
signal, digital power-good to U26, and two master-enable branches. The change
adds 25 trace segments, five signal vias and three ground-stitch vias. Components,
original copper, zone outlines and schematic nets are unchanged.

The three reference-plane transitions each have a main-ground stitch about
0.90 mm from the signal via. The other two signal vias retain the same adjacent
reference plane. This is a checked layout arrangement, not measured timing or
signal-integrity qualification.

The [native checks](review.json) report zero geometry/parity errors and the two
retained isolated-reference ERC warnings. The [independent audit](startup-control-review.json)
verifies the five exact native group merges, all other original connectivity,
**1,618 retained reference checks**, ten new referenced paths, all eleven supply
planes and all seven quiet-ground networks. The historical unanchored ground
fragment remains excluded from return credit.

An earlier trial passed native DRC but cut the DC-input planes. Its
[rejection record](../two-board-power-startup-controls-native-02/rejection-review.json)
is retained. This revision moves the shared master-enable transition outside
those planes; their complete filled geometry is unchanged.

Seven native copper detail views were visually inspected:
[latch bottom](plots/startup-arm-back.png),
[latch In6 reference](plots/startup-arm-inner6.png),
[controls front](plots/startup-controls-front.png),
[controls bottom](plots/startup-controls-back.png),
[controls In1 reference](plots/startup-controls-inner1.png),
[controls In2 routing](plots/startup-controls-inner2.png), and
[controls In6 reference](plots/startup-controls-inner6.png).

The [updated startup inventory](../two-board-startup-connectivity-survey-07/README.md)
has **53 missing joins across 30 open nets**, down from 58 across 32. The
[pad-access survey](../two-board-startup-reference-access-01/survey.json) identifies
22 still-open logic pads without full adjacent ground coverage at the center
of a 0.2 mm trace launch. These locations need reference repair or a different
escape arrangement before more routing can be accepted.

**Not ready for fabrication.** The signal board still has 251 opens and lacks
the approved ESS codec footprint. AUX distribution, loading/startup/thermal
qualification, installed housing fit, accepted stackup, complete BOM and
manufacturing outputs remain unfinished. This candidate retains the TBP51
feedback-part qualification limits. It does not replace the selected public
[TBP50 checkpoint](../two-board-fabrication-status-50/status.json).
