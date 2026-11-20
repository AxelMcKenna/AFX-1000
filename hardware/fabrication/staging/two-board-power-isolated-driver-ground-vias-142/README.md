# Local power-board ground returns

The control-side ground pins of isolated drivers E_U2 and E_U4 each connect to the adjacent In1.Cu ground plane through a new 0.60 mm via with a 0.30 mm drill. KiCad verifies 2 pad-group joins and 1,210 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.30 | E_U2:4 to P_C103:2 | F.Cu | 1.05 |
| 0.30 | E_U4:4 to P_C103:2 | F.Cu | 0.70 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
