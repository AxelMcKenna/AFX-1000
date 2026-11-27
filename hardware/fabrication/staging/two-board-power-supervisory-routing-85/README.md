# Supervisory signal routing

Each 0.20 mm trace has a continuous adjacent ground reference tied to an existing system-ground via. KiCad verifies 3 intended joins and 1,393 remaining open connections.

| Signal | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| P03_MON_BUCK_OK | P_U26:4 to P_U25:5 | B.Cu | 12.99 |
| 5V_DIG_OV_OK | M_U4:13 to M_R101:2 | F.Cu | 33.54 |
| N12_ARM_CONDITIONED | N_U39:1 to N_U54:1 | F.Cu | 46.81 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Ground and refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
