# Rail-monitor status connections

The negative bias status outputs now connect to their receiving logic. Each route uses 0.20 mm traces and two 0.30 mm through drills with 0.60 mm lands. Native refill checks cover the connected ground along every leg and verify previously connected pad groups. KiCad verifies 2 pad-group joins and 1,005 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | M_R71:1 to M_U3:13 | F.Cu, In2.Cu | 40.72 |
| 0.20 | M_U10:3 to M_U11:9 | F.Cu, In5.Cu | 23.77 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The maximum modeled change in inlet-plane sheet resistance was 0.245%. [Mesh calculations](inlet-sheet-comparison.json)

The filled digital 5 V plane matches the previous revision. [Native comparison](digital-sheet.json)

The eight-layer survey records 0 package-midline intersections. [Whole-board survey](isolation-midlines.json)
