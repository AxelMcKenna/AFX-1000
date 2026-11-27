# Rail-monitor status connections

3 rail-monitor status signals now connect to their receiving gates or comparator pull-ups. Each uses 0.20 mm traces and two 0.30 mm through drills with 0.60 mm lands. Native refill checks cover the connected ground along every leg and verify previously connected pad groups. KiCad verifies 3 pad-group joins and 1,011 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | M_U10:8 to M_U11:12 | F.Cu, In5.Cu | 8.80 |
| 0.20 | M_U2:14 to M_R42:1 | F.Cu, In5.Cu | 25.65 |
| 0.20 | M_U3:2 to M_R55:2 | F.Cu, In5.Cu | 37.35 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The maximum modeled change in inlet-plane sheet resistance was 0.308%. [Mesh calculations](inlet-sheet-comparison.json)

Two mesh resolutions compared nine pairs of ports across the changed digital 5 V pour. The largest modeled sheet resistance change was 0.523%. [Digital 5 V sheet model](digital-sheet.json)

The eight-layer survey records 4 package-midline intersections. [Whole-board survey](isolation-midlines.json)
