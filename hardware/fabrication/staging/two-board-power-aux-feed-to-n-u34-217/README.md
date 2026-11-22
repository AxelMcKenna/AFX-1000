# Auxiliary supply connection to N_U34

The 2.5 V auxiliary regulator now reaches N_U34 pin 5. The new 0.25 mm front trace terminates at the existing supply junction near N_R91. Continuous ground on In1 supports the entire branch. The connection adds no vias. KiCad verifies 1 pad-group joins and 1,019 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.25 | N_U34:5 to N_R91:1 | F.Cu | 2.75 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records the same 12 package-midline intersections as the previous board. [Whole-board survey](isolation-midlines.json)
