# Monitor and auxiliary supply branches

The 0.40 mm branches distribute the monitor and fan supplies, auxiliary power and protection reference. Adjacent grounded inner-layer copper backs each branch. KiCad verifies 8 intended joins and 1,275 remaining connections. Loaded reference accuracy and noise still need measurement.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.40 | M_C44:1 to M_C43:1 | F.Cu | 14.68 |
| 0.40 | M_U9:14 to M_C44:1 | F.Cu | 18.97 |
| 0.40 | M_R79:1 to M_C46:1 | F.Cu | 15.29 |
| 0.40 | E_R75:1 to E_R59:1 | B.Cu | 18.86 |
| 0.40 | F_U12:5 to F_C5:1 | F.Cu | 24.20 |
| 0.40 | E_U12:14 to P_D102:3 | B.Cu | 23.14 |
| 0.40 | P_C401:1 to P_D102:3 | F.Cu | 21.33 |
| 0.40 | P_R246:1 to N_U40:14 | F.Cu | 18.95 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
