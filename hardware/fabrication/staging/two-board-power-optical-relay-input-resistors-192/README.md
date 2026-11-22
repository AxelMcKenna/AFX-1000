# Optical relay input resistors

N_R5 shunts the two optical input contacts on the front of N_U5. N_R4 joins the same plated input contact from the rear. The three traces replace one remote jumper trace and add no vias. The modeled assembly clearances are recorded in [component placement](component-placement.json). KiCad verifies 2 pad-group joins and 1,071 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | N_R5:1 to N_U5:1 | F.Cu | 5.33 |
| 0.20 | N_R5:2 to N_U5:2 | F.Cu | 2.17 |
| 0.20 | N_R4:2 to N_U5:1 | B.Cu | 4.65 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records the same 38 package-midline intersections as the previous board. [Whole-board survey](isolation-midlines.json)
