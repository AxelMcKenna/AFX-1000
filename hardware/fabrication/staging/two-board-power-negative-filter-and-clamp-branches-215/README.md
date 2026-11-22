# Negative rail filter and clamp connections

Three capacitor branches in the negative rail circuits use 0.65 mm copper. Separate 0.35 mm traces link the −12 V ramp capacitors and the clamp LED supply switch to its series resistor. All five connections are on a single surface with continuous adjacent ground and use no vias. KiCad verifies 5 pad-group joins and 1,020 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.65 | N_C34:2 to N_C53:2 | B.Cu | 2.92 |
| 0.65 | N_C8:2 to N_C10:2 | B.Cu | 4.81 |
| 0.65 | N_C16:2 to N_C19:2 | F.Cu | 7.25 |
| 0.35 | N_C41:1 to N_C44:1 | F.Cu | 3.63 |
| 0.35 | N_U57:6 to N_R11:1 | F.Cu | 4.29 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records the same 14 package-midline intersections as the previous board. [Whole-board survey](isolation-midlines.json)
