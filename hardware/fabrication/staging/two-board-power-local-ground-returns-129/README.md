# Local power-board ground returns

Ground traces connect the listed lands to existing vias in the common PWR_AGND copper. The F_C403 return also passes through the center of E_C34 pad 2. KiCad verifies 12 pad-group joins and 1,230 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.50 | M_C38:2 to P_C103:2 | F.Cu | 4.19 |
| 0.50 | F_U301:2 to P_C103:2 | F.Cu | 7.60 |
| 0.50 | F_C6:2 to P_C103:2 | F.Cu | 3.54 |
| 0.50 | F_R303:2 to P_C103:2 | F.Cu | 6.23 |
| 0.50 | F_C403:2 to P_C103:2 | B.Cu | 8.52 |
| 0.50 | F_C404:2 to P_C103:2 | B.Cu | 5.00 |
| 0.50 | P_R402:2 to P_C103:2 | F.Cu | 5.85 |
| 0.50 | E_C36:2 to P_C103:2 | F.Cu | 0.90 |
| 0.50 | E_C29:2 to P_C103:2 | F.Cu | 2.54 |
| 0.50 | E_C40:2 to P_C103:2 | B.Cu | 1.30 |
| 0.50 | E_C42:2 to P_C103:2 | B.Cu | 2.25 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
