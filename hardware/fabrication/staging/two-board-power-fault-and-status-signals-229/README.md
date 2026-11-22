# Protection and status connections

These traces connect the fault and status pads listed below. Each route uses 0.20 mm traces and two 0.30 mm through drills with 0.60 mm lands. Native refill checks cover the connected ground along every leg and verify previously connected pad groups. KiCad verifies 5 pad-group joins and 1,000 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | N_R66:2 to N_U20:6 | F.Cu, In5.Cu | 12.42 |
| 0.20 | E_U18:13 to E_U39:6 | B.Cu, In5.Cu, F.Cu | 13.90 |
| 0.20 | E_U37:7 to E_U11:4 | B.Cu, In5.Cu, F.Cu | 15.10 |
| 0.20 | E_R68:1 to E_U9:14 | B.Cu, In5.Cu, F.Cu | 23.41 |
| 0.20 | E_R125:2 to E_U38:6 | B.Cu, In2.Cu, F.Cu | 30.17 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The maximum modeled change in inlet-plane sheet resistance was 0.038%. [Mesh calculations](inlet-sheet-comparison.json)

The filled digital 5 V plane matches the previous revision. [Native comparison](digital-sheet.json)

The eight-layer survey records 0 package-midline intersections. [Whole-board survey](isolation-midlines.json)
