# Rail monitor feedback placement

M_C33, M_C34, M_C35 and their three parallel feedback resistors sit on the rear face near M_U5. Each resistor and capacitor pair shares its two feedback vias. The refill comparison reports any ground-edge growth outside the added reference copper. The modeled assembly clearances are recorded in [component placement](component-placement.json). KiCad verifies 12 pad-group joins and 1,123 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | M_C33:1 to M_U5:1 to M_R103:1 | B.Cu, F.Cu | 2.69 |
| 0.20 | M_C33:2 to M_U5:2 to M_R103:2 | B.Cu, F.Cu | 3.21 |
| 0.20 | M_C34:1 to M_U5:7 to M_R105:1 | B.Cu, F.Cu | 2.18 |
| 0.20 | M_C34:2 to M_U5:6 to M_R105:2 | B.Cu, F.Cu | 2.21 |
| 0.20 | M_C35:1 to M_U5:8 to M_R107:1 | B.Cu, F.Cu | 2.19 |
| 0.20 | M_C35:2 to M_U5:9 to M_R107:2 | B.Cu, F.Cu | 2.11 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
