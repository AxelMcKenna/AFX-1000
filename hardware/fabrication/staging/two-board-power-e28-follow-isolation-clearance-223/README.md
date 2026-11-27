# Analog-follow trace clearance at E_U1

The E28 analog-follow signal now passes around E_U1. Two traces meet the existing endpoint vias through one new 0.60 mm land with a 0.30 mm drill. Native refill checks cover the adjacent ground and every named pad group. The surface traces use the adjacent ground planes. The only new obstruction on the inlet planes is the via clearance. KiCad verifies 0 pad-group joins and 1,011 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | E_U31:7 to E_U14:1 | B.Cu, F.Cu | 35.39 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The maximum modeled change in inlet-plane sheet resistance was 0.048%. [Mesh calculations](inlet-sheet-comparison.json)

The eight-layer survey records 3 package-midline intersections, one fewer than the previous board. [Whole-board survey](isolation-midlines.json)
