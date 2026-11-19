# Negative rail monitor amplifier ground connections

The OPA4192 monitor amplifier has a dedicated supply-return via and short 0.30 mm reference-input traces. The new 0.60 mm via lands contact the existing In4 ground plane. The layout check measures copper remaining around the antipads in both DC input pours. Loaded current and temperature performance remain to be measured. KiCad verifies 5 intended joins and 1,362 remaining open connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.30 | M_U5:3 to P_C103:2 | F.Cu | 3.40 |
| 0.30 | M_U5:5 to P_C103:2 | F.Cu | 3.40 |
| 0.30 | M_U5:11 to P_C103:2 | F.Cu | 1.48 |
| 0.30 | M_U5:10 to P_C103:2 | F.Cu | 2.20 |
| 0.30 | M_U5:12 to P_C103:2 | F.Cu | 2.20 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Ground and refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
