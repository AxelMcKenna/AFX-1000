# Linear regulator inputs and positive 12 V output tab

P_U8 has a direct connection between its positive 12 V output lead and its copper tab. P_U8 joins its input and control supply pins. At P_U10 and P_U11 the input leads, input-connected exposed pad and current-limit strap share the raw input rail on the front layer. KiCad verifies 6 intended joins and 1,326 remaining open connections. Thermal performance and downstream distribution remain open.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 1.50 | P_U8 pads 4 and 5 | F.Cu | 1.70 |
| 0.40 | P_U10 pads 9 and 10 | F.Cu | 0.50 |
| 0.35 | P_U10 pads 8 and 9 | F.Cu | 0.50 |
| 0.80 | P_U10 pads 9 and 11 | F.Cu | 1.45 |
| 0.40 | P_U11 pads 9 and 10 | F.Cu | 0.50 |
| 1.20 | P_U8 pads 3 and 3 | F.Cu | 9.15 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
