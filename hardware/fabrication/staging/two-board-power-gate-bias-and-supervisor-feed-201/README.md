# Gate bias and supervisor supply

Joined the positive 12 V gate series resistor to its bias resistor on rear copper. On front copper, the negative 12 V controller supply joins N_R79 to the TPS3890 supervisor. Both routes remain on one layer with continuous adjacent reference copper. The MOSFET gate and the remaining supply distribution still require routing. KiCad verifies 2 pad-group joins and 1,053 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | E_R17:2 to E_R18:1 | B.Cu | 2.36 |
| 0.20 | N_R79:1 to N_U26:4 | F.Cu | 5.07 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records the same 25 package-midline intersections as the previous board. [Whole-board survey](isolation-midlines.json)
