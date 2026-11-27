# Low-voltage converter feedback return

A 0.365 mm trace connects P_U13 pin 5 (FB2N) directly to its exposed ground pad. The geometry follows the corresponding connection on P_U1. The exposed pad still needs its connection to system ground. KiCad verifies 1 pad-group join and 1,209 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.40 | P_U13:5 to P_U13:11 | F.Cu | 0.36 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
