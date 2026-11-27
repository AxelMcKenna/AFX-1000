# Inner layer clearance at E_U1 and E_U2

The ANA_PG1 and 2.5 V auxiliary traces on In6 now pass around E_U1 and E_U2 respectively. Both retain their endpoints, original 0.20 mm width and adjacent In5 ground coverage. The auxiliary trace increases by 0.83 mm and the power-good trace by 1.55 mm. KiCad verifies 0 pad-group joins and 1,020 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | E_R99:1 to E_U14:3 | In6.Cu | 13.55 |
| 0.20 | E_C36:1 to E_R83:1 | In6.Cu | 43.29 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records 12 package-midline intersections, two fewer than the previous board. [Whole-board survey](isolation-midlines.json)
