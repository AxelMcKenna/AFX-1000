# Connect the positive rail bleeders and auxiliary reference divider

Three 0.35 mm traces connect the 9.09 kΩ P_R24 and 5.62 kΩ P_R29 bleeders to their positive output capacitor groups and the 12.4 kΩ E_R83 reference divider to the auxiliary rail. Each branch uses the adjacent ground plane. KiCad verifies 3 pad-group joins and 1,137 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.35 | P_C38:1 to P_R24:1 | B.Cu | 2.19 |
| 0.35 | E_R83:1 to E_R92:1 | B.Cu | 11.69 |
| 0.35 | P_R29:1 to P_C43:1 | B.Cu | 19.73 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
