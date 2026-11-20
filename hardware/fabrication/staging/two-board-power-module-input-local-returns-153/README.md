# Local module-feed capacitor connections

P_C4 and P_C70 reach the In2.Cu module-feed plane on separate 0.60 mm traces and 0.60/0.30 mm vias. On In6.Cu, ground copper follows each trace back to that capacitor's own ground via. KiCad verifies 2 pad-group joins and 1,176 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.60 | P_C4:1 to P_U101:17 | B.Cu | 1.35 |
| 0.60 | P_C70:1 to P_U101:17 | B.Cu | 1.57 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
