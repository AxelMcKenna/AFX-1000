# Positive raw supply capacitor ground returns

Two rear-layer 0.60 mm traces connect the grounded terminals of P_C36 (10 µF) and P_C59 (100 nF) to existing system ground vias. Both capacitors serve the raw positive supply. Their supply terminals still require routing. KiCad verifies 2 intended pad-group joins and 1,310 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.60 | P_C36:2 to P_C103:2 | B.Cu | 1.69 |
| 0.60 | P_C59:2 to P_C103:2 | B.Cu | 1.18 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
