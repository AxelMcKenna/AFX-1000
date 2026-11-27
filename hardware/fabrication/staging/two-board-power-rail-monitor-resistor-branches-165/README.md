# Connect the rail monitor resistor branches

Four 0.35 mm traces connect the supply ends of M_R1, E_R32, E_R23 and N_R75. Each branch serves a resistor of at least 15 kΩ and uses the adjacent ground plane. KiCad verifies 4 pad-group joins and 1,140 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.35 | M_J2:1 to M_R1:1 | F.Cu | 3.15 |
| 0.35 | N_U22:6 to N_R75:2 | F.Cu | 9.32 |
| 0.35 | E_C16:2 to E_R32:1 | F.Cu | 10.16 |
| 0.35 | E_J3:4 to E_R23:1 | B.Cu | 15.94 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
