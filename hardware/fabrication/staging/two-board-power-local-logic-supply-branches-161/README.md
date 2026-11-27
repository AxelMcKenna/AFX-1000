# Local logic supply and reference branches

The 0.30 mm surface traces connect existing auxiliary, fan and monitor pad groups. They use the adjacent ground planes without adding vias. The reference-layer review checks the copper under each trace and its connection to system ground. KiCad verifies 13 pad-group joins and 1,149 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.30 | F_J5:2 to F_C17:1 | F.Cu | 0.51 |
| 0.30 | F_U16:5 to F_C19:1 | F.Cu | 0.91 |
| 0.30 | N_J1:1 to N_C79:1 | B.Cu | 1.01 |
| 0.30 | E_J5:1 to E_C25:1 | F.Cu | 1.68 |
| 0.30 | N_U16:1 to N_U27:8 | F.Cu | 2.43 |
| 0.30 | N_U16:5 to N_U37:14 | F.Cu | 2.56 |
| 0.30 | P_R113:1 to P_C107:1 | B.Cu | 4.74 |
| 0.30 | N_U1:7 to N_C89:1 | F.Cu | 7.94 |
| 0.30 | N_U8:7 to P_R246:1 | F.Cu | 8.29 |
| 0.30 | M_R55:1 to M_R24:1 | F.Cu | 8.90 |
| 0.30 | M_R27:1 to M_R40:1 | F.Cu | 10.32 |
| 0.30 | M_R15:1 to M_R68:1 | F.Cu | 10.76 |
| 0.30 | M_R6:1 to M_R72:1 | F.Cu | 11.05 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
