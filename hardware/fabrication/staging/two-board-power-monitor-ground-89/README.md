# Monitor divider and logic ground returns

Short 0.40 mm traces and 0.60 mm vias with 0.30 mm drills join these resistor returns to the main ground plane. The routing checks verify the contact from each resistor pad to the plane. Loaded current and temperature performance remain to be measured. KiCad verifies 8 intended joins and 1,373 remaining open connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.40 | P_R309:2 to P_C103:2 | F.Cu | 2.67 |
| 0.40 | P_R307:2 to P_C103:2 | F.Cu | 4.50 |
| 0.40 | P_R301:2 to P_C103:2 | F.Cu | 1.71 |
| 0.40 | P_R305:2 to P_C103:2 | B.Cu | 3.86 |
| 0.40 | E_R84:2 to P_C103:2 | B.Cu | 1.95 |
| 0.40 | M_R26:2 to P_C103:2 | F.Cu | 2.77 |
| 0.40 | N_R78:2 to P_C103:2 | F.Cu | 4.64 |
| 0.40 | F_R14:2 to P_C103:2 | F.Cu | 2.04 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Ground and refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
