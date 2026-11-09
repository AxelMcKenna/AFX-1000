# TBP53 startup pin-access repair

This checked working candidate repairs ground-reference coverage and routing
access around E_U22, E_U23 and E_U28. Open the [KiCad project](power_protection.kicad_pro).
It preserves all native connection groups from
[TBP52](../two-board-power-startup-controls-native-03/README.md): power-board
opens remain **2,167**. This step prepares the remaining startup routing.

The repair moves the U22 feedback bridge inside its pad rows, detours obstructing
digital-power-good and GLOBAL_MASTER traces, reroutes a local AUX branch, and
extends the main In6 ground outline. It replaces 21 track segments and two vias
with 36 segments, four signal vias and six ground stitches. One replaced AUX via
moves to (131.75, 157.25) mm; the second removed via became obsolete when both
incident ALL_RAILS_ALLOW traces moved onto In3. No component placements or
schematic nets change.

The [independent audit](startup-access-review.json) verifies **21 clear 0.2 mm
trace-launch corridors**, at least 2.5 mm long, with full-width adjacent ground
coverage. Twelve previously uncovered pad centers are repaired. The updated
[access survey](../two-board-startup-reference-access-02/survey.json) records
65 of 75 selected still-open logic pads covered, with ten remaining uncovered.
These corridors are not yet routed connections.

All **1,622 retained reference checks** and 14 replacement-path checks pass.
All eleven supply-plane fills, seven quiet-ground networks, other zone outlines,
and the excluded unanchored fragment are preserved. Transition stitches meet
declared geometric targets of 2 mm for logic and 3 mm for AUX power. These are
layout targets, not manufacturer limits or measured electrical qualification.

[Native checks](review.json) report zero geometry/parity/ERC errors and the two
retained isolated-reference ERC warnings. The first trial's obsolete-via warning
is preserved in its [rejection record](../two-board-power-startup-access-native-01/rejection-review.json).
The [startup inventory](../two-board-startup-connectivity-survey-08/inventory.json)
still contains 53 missing joins across 30 open nets.

Thirteen native views were [visually inspected](visual-review.json):
[startup front](plots/startup-access-full-front.png),
[startup bottom](plots/startup-access-full-back.png),
[In1](plots/startup-access-full-inner1.png),
[In3](plots/startup-access-full-inner3.png),
[In4](plots/startup-access-full-inner4.png),
[In5](plots/startup-access-full-inner5.png),
[In6](plots/startup-access-full-inner6.png),
[master front](plots/startup-master-full-front.png),
[master bottom](plots/startup-master-full-back.png),
[master In1](plots/startup-master-full-inner1.png),
[master In2 bridge](plots/startup-master-transition-inner2.png),
[master In5](plots/startup-master-full-inner5.png), and
[master In6](plots/startup-master-full-inner6.png).

**Not ready for fabrication.** The signal board still has 251 opens and lacks
the approved ESS footprint. Remaining routing, AUX supply/load/startup/thermal
qualification, installed housing fit, accepted stackup, BOM and manufacturing
outputs remain unfinished. This working candidate does not replace the selected
public [TBP50 checkpoint](../two-board-fabrication-status-50/status.json).
