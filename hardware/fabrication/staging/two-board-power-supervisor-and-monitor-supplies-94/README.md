# Auxiliary logic and rail monitor supply branches

The 2.5 V rail feeds N_U58 through the nearby N_U28 supply connection. M_R38 joins the monitor 3.3 V rail at M_R43. Both 0.40 mm traces have a continuous ground reference tied to an existing ground via. Loaded current and temperature performance remain to be measured. KiCad verifies 2 intended joins and 1,358 remaining open connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.40 | N_U58:5 to N_U28:5 | F.Cu | 10.21 |
| 0.40 | M_R43:1 to M_R38:1 | F.Cu | 14.47 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Ground and refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
