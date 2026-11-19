# Local ground returns

Six inner-layer traces join plated component and connector pads to existing system-ground copper. The full trace end lands inside the ground field at each of those six pads. A separate 1.70 mm front-layer trace joins the M_U2 comparator supply return to an existing ground track. Loaded current and temperature performance remain to be measured. KiCad verifies 7 intended joins and 1,381 remaining open connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.65 | E_J9:1 to P_C103:2 | In1.Cu | 1.52 |
| 2.00 | E_C16:1 to P_C103:2 | In4.Cu | 2.61 |
| 2.50 | E_C4:2 to P_C103:2 | In1.Cu | 3.41 |
| 1.40 | F_J201:2 to P_C103:2 | In1.Cu | 3.35 |
| 1.00 | F_C203:2 to P_C103:2 | In6.Cu | 5.28 |
| 1.00 | F_J401:2 to P_C103:2 | In1.Cu | 8.30 |
| 0.40 | M_U2:12 to P_C103:2 | F.Cu | 1.70 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Ground and refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
