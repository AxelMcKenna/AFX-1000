# Negative regulator compensation placement

P_C54 sits on the rear face beside P_U6. Two rear-layer traces connect this compensation capacitor between pins 6 and 7 of the OPA2192. The second compensation capacitor, P_C49, still needs routing. The refill comparison reports any ground-edge growth outside the added reference copper. The modeled assembly clearances are recorded in [component placement](component-placement.json). KiCad verifies 2 pad-group joins and 1,112 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | P_C54:1 to P_U6:7 | B.Cu | 5.01 |
| 0.20 | P_C54:2 to P_U6:6 | B.Cu | 3.26 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
