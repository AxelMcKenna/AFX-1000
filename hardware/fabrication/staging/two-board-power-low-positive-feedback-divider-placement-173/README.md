# Low positive regulator feedback divider placement

The 15 kΩ P_R45 feedback resistor sits on the rear face beside P_U13. One via reaches the feedback pin. The other resistor pad returns to the regulator ground group through an existing plated via. The refill comparison reports any ground-edge growth outside the added reference copper. The modeled assembly clearances are recorded in [component placement](component-placement.json). KiCad verifies 2 pad-group joins and 1,114 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | P_R45:1 to P_U13:1 | B.Cu, F.Cu | 6.50 |
| 0.20 | P_R45:2 to P_U13:5 | B.Cu | 0.71 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
