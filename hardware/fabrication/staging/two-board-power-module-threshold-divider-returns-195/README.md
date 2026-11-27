# Module undervoltage and overvoltage divider returns

G_R2 and G_R4 connect the TPS26601 undervoltage and overvoltage sense pins to their lower divider resistors. Both resistors return to the controller RTN connection at G_R5 pin 2. The upper divider feeds remain unfinished. All four connections use front copper, with no new vias or plane changes. The modeled assembly clearances are recorded in [component placement](component-placement.json). KiCad verifies 4 pad-group joins and 1,065 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | G_R2:1 to G_U1:10 | F.Cu | 2.96 |
| 0.20 | G_R2:2 to G_R5:2 | F.Cu | 5.68 |
| 0.20 | G_R4:1 to G_U1:12 | F.Cu | 2.67 |
| 0.20 | G_R4:2 to G_R5:2 | F.Cu | 3.66 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records the same 28 package-midline intersections as the previous board. [Whole-board survey](isolation-midlines.json)
