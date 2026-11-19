# Fan logic bypass capacitor placement

F_C5 and F_C19 move next to F_U3 and F_U13 on the rear of the board. Each 100 nF capacitor connects to its IC supply pin through one via and to a nearby ground via on the rear. Both local bypass branches still need a connection to the fan regulator supply. Supplier height and physical enclosure fit remain unqualified. KiCad verifies 4 intended joins and 1,352 remaining open connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.35 | F_C5:1 to F_U3:5 | F.Cu | 6.90 |
| 0.35 | F_C5:2 to P_C103:2 | B.Cu | 1.19 |
| 0.35 | F_C19:1 to F_U13:5 | F.Cu | 4.64 |
| 0.35 | F_C19:2 to P_C103:2 | B.Cu | 1.30 |

[Capacitor placement](component-placement.json) · [Routes](routes.json) · [Connectivity](connectivity.json) · [Ground and refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
