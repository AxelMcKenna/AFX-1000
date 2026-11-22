# Monitor comparator hysteresis placement

M_R29 sits on the front face next to M_U2. The feedback resistor connects pins 2 and 5 with short front-layer traces. The refill comparison reports any ground-edge growth outside the added reference copper. The modeled assembly clearances are recorded in [component placement](component-placement.json). KiCad verifies 2 pad-group joins and 1,110 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | M_R29:1 to M_U2:2 | F.Cu | 1.43 |
| 0.20 | M_R29:2 to M_U2:5 | F.Cu | 1.51 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
