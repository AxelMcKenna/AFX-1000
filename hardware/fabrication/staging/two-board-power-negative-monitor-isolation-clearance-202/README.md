# Negative output monitor clearance at N_U11

Moved both resistors of the negative 19 V output monitor clear of the N_U11 contact gap. The summing-node trace remains 3.50 mm. The inverter output now reaches N_R24 using a 13.30 mm segment chain over connected In6 ground, replacing its previous 1.93 mm terminal segment. The three rear-side crossings at this package have cleared. The inner-layer crossing still requires work. See [placements](component-placement.json). KiCad verifies 0 pad-group joins and 1,053 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | N_R23:2 to N_R24:2 | B.Cu | 3.50 |
| 0.20 | N_R28:1 to N_R24:1 | B.Cu | 13.30 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records 22 package-midline intersections, three fewer than the previous board. [Whole-board survey](isolation-midlines.json)
