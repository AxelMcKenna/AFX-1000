# Local ground returns

The OPA4192 spare input P_U5 pin 10, module feed bypass capacitor P_C255 and regulator set capacitor P_C241 each connect to system ground through a 0.50 mm trace and a dedicated via. KiCad verifies contact with the two inner ground planes, 3 intended pad-group joins and 1,289 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.50 | P_U5:10 to P_C103:2 | F.Cu | 2.22 |
| 0.50 | P_C255:2 to P_C103:2 | F.Cu | 1.27 |
| 0.50 | P_C241:2 to P_C103:2 | B.Cu | 1.43 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
