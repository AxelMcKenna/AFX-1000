# Disconnect monitor auxiliary supply

E_C67 pin 1 and E_U22 pin 14 reach the 2.5 V regulator through a 0.30 mm rear trace and a 0.60/0.30 mm via on the existing In3.Cu supply branch. KiCad verifies 1,167 remaining connections. The route increases the regulator's reach by two pads.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.30 | E_C67:1 to P_U102:1 | B.Cu | 0.90 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
