# Protection and status connections

These traces connect the fault and status pads listed below. Each route uses 0.20 mm traces and two 0.30 mm through drills with 0.60 mm lands. Native refill checks cover the connected ground along every leg and verify previously connected pad groups. KiCad verifies 3 pad-group joins and 994 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | F_R4:1 to F_U16:2 | F.Cu, In5.Cu | 12.11 |
| 0.20 | E_U12:2 to E_U11:6 | B.Cu, In2.Cu, F.Cu | 36.50 |
| 0.20 | F_R15:1 to F_U3:3 | F.Cu, In2.Cu | 36.95 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The filled digital 5 V plane matches the previous revision. [Native comparison](digital-sheet.json)

The eight-layer survey records 0 package-midline intersections. [Whole-board survey](isolation-midlines.json)
