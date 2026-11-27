# Fan reset timing and rail monitor reference capacitors

F_C14 moves behind the reset supervisor and M_C4 moves behind the rail monitor comparator. Each capacitor connects to its IC through one 0.30 mm drilled via and has a short rear-side ground trace. The placement report records the original separation, final trace lengths and nearest component clearances. Supplier height and physical enclosure fit remain unqualified. KiCad verifies 4 intended joins and 1,367 remaining open connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | F_C14:1 to F_U9:5 | F.Cu | 6.15 |
| 0.30 | F_C14:2 to P_C103:2 | B.Cu | 3.84 |
| 0.20 | M_C4:1 to M_U1:7 | F.Cu | 4.99 |
| 0.30 | M_C4:2 to P_C103:2 | B.Cu | 1.23 |

[Capacitor placement](component-placement.json) · [Routes](routes.json) · [Connectivity](connectivity.json) · [Ground and refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
