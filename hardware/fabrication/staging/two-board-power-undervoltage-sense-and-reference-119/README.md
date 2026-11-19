# Undervoltage sensing and reference returns

The monitor and startup undervoltage networks use 0.20 mm traces and 0.60 mm through vias with 0.30 mm drills. Grounded copper backs each trace and its layer transitions. KiCad verifies 4 intended pad-group joins and 1,270 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | N_U14:2 to N_R34:2 | F.Cu | 7.71 |
| 0.20 | N_U14:5 to N_R52:2 | F.Cu | 10.12 |
| 0.20 | M_R5:2 to M_U1:5 | F.Cu | 10.12 |
| 0.20 | N_R27:1 to N_R26:2 | B.Cu | 13.27 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
