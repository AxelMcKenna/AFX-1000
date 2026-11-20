# Module-feed input bypass connections

The positive pads of the 22 µF input capacitors P_C2 and P_C3 reach the existing In2.Cu module-feed plane through separate 0.60/0.30 mm vias. Both 0.60 mm traces are shorter than 1 mm. The adjacent ground plane covers the trace beyond the original pad and via clearance. KiCad verifies 2 pad-group joins and 1,178 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.60 | P_C3:1 to P_U101:17 | F.Cu | 0.82 |
| 0.60 | P_C2:1 to P_U101:17 | F.Cu | 0.76 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
