# Negative 19 V hot-swap gate and current sensing

On the negative 19 V hot-swap circuit the LTC4261 SENSE lead terminates directly on the sense resistor land. The gate drive terminates at the pass MOSFET gate. Both routes stay on front copper over a connected ground reference. The opposite shunt sense connection, load-current path and energized current limit remain open for verification. KiCad verifies 2 pad-group joins and 1,059 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | N_U18:14 to N_R69:2 | F.Cu | 3.28 |
| 0.20 | N_U18:15 to N_Q1:1 | F.Cu | 3.55 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records the same 28 package-midline intersections as the previous board. [Whole-board survey](isolation-midlines.json)
