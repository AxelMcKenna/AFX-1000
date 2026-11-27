# Regulator and eFuse pin connections

Short traces join the two negative-regulator output pads, the LT3471 reference and positive feedback input pairs, and the parallel power pads of the eFuses. Each trace terminates inside both named lands. KiCad verifies 9 pad-group joins and 1,260 remaining connections. Load-current and temperature-rise measurements remain outstanding.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.32 | P_U10:1 to P_U10:2 | F.Cu | 0.50 |
| 0.25 | P_U1:2 to P_U1:3 | F.Cu | 0.50 |
| 0.25 | P_U13:2 to P_U13:3 | F.Cu | 0.50 |
| 0.52 | E_U14:6 to E_U14:11 | F.Cu | 0.90 |
| 0.72 | E_U15:6 to E_U15:11 | F.Cu | 0.90 |
| 0.72 | E_U16:6 to E_U16:11 | F.Cu | 0.90 |
| 0.72 | E_U17:6 to E_U17:11 | F.Cu | 0.90 |
| 0.72 | E_U33:6 to E_U33:11 | F.Cu | 0.90 |
| 0.52 | E_U14:5 to E_U14:12 | F.Cu | 0.90 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
