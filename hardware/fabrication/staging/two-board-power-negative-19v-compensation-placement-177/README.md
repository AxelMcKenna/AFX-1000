# Negative 19 V regulator compensation placement

P_C49 sits beside the OPA2192 amplifier P_U6. Two rear-layer traces connect the compensation capacitor to pins 1 and 2, with clearance to the adjacent negative 12 V divider ground via. The refill comparison reports any ground-edge growth outside the added reference copper. The modeled assembly clearances are recorded in [component placement](component-placement.json). KiCad verifies 2 pad-group joins and 1,106 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | P_C49:1 to P_U6:1 | B.Cu | 8.54 |
| 0.20 | P_C49:2 to P_U6:2 | B.Cu | 6.60 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
