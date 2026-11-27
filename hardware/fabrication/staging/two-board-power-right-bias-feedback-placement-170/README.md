# Right bias feedback placement

M_C36 and M_R109 share two feedback vias near M_U5. M_R108 joins their summing node on the rear face. The refill comparison reports any ground-edge growth outside the added reference copper. The modeled assembly clearances are recorded in [component placement](component-placement.json). KiCad verifies 4 pad-group joins and 1,119 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | M_C36:1 to M_U5:14 to M_R109:1 | B.Cu, F.Cu | 2.23 |
| 0.20 | M_C36:2 to M_U5:13 to M_R109:2 to M_R108:2 | B.Cu, F.Cu | 3.93 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
