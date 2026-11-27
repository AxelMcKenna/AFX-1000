# Overvoltage comparator feedback placement

E_R81 connects the E_U10 overvoltage comparator output to its feedback reference input. The modeled assembly clearances are recorded in [component placement](component-placement.json). KiCad verifies 2 pad-group joins and 1,076 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | E_R81:1 to E_U10:1 | B.Cu, F.Cu | 2.78 |
| 0.20 | E_R81:2 to E_U10:7 | B.Cu, F.Cu | 6.51 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records the same 51 package-midline intersections as the previous board. [Whole-board survey](isolation-midlines.json)
