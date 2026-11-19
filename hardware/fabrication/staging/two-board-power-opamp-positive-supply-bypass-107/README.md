# OPA4192 positive supply bypass

One 0.50 mm path connects the positive supply pin of P_U5 to the 100 nF bypass capacitor P_C59 through a single via. The capacitor's ground pad reaches a separate system ground via. Both external traces reference grounded inner copper. The raw supply still requires upstream distribution. KiCad verifies one intended join and 1,309 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.50 | P_C59:1 to P_U5:4 | F.Cu | 2.13 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
