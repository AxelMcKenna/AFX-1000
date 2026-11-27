# Main Ćuk converter rectifier return

The rectifier cathode P_D2 pin 1 and output reservoir P_C9 pin 2 connect to opposite faces of the same existing system-ground via. The front return is 0.98 mm long and the rear return is 1.63 mm long. Both traces are 1.20 mm wide. KiCad verifies 2 pad-group joins and 1,193 remaining connections. Current capacity, ripple and switching-loop performance still need verification.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 1.20 | P_D2:1 to P_C103:2 | F.Cu | 0.98 |
| 1.20 | P_C9:2 to P_C103:2 | B.Cu | 1.63 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
