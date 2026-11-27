# Negative-rail controller resistor returns

Three 0.35 mm surface traces connect N_R58, N_R59 and N_R77 to their schematic negative-rail pad groups. The traces are under 2.4 mm long and use the adjacent ground planes. The reference-layer review checks the copper under each trace and its connection to system ground. KiCad verifies 3 pad-group joins and 1,146 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.35 | N_U18:25 to N_R58:2 | F.Cu | 1.78 |
| 0.35 | N_R59:1 to N_R58:2 | F.Cu | 1.90 |
| 0.35 | N_R77:2 to P_U11:1 | F.Cu | 2.38 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
