# Negative hot-swap source and shunt connections

Each negative hot-swap MOSFET source connects directly to its current-sense shunt on front copper. Both force connections use a single 1.00 mm trace with no vias. At N_R69 the pre-existing controller sense lead meets the force path at the shunt land. Outside that land, native copper polygons verify at least 0.20 mm separation. Fault-current, heating and the rest of each power path still require verification. KiCad verifies 2 pad-group joins and 1,051 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 1.00 | N_Q1:3 to N_R69:2 | F.Cu | 5.69 |
| 1.00 | N_Q2:3 to N_R86:2 | F.Cu | 5.76 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records the same 19 package-midline intersections as the previous board. [Whole-board survey](isolation-midlines.json)
