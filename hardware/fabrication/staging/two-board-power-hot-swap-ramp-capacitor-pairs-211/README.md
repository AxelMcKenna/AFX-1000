# Hot-swap ramp capacitor pairs

The −19 V and −12 V hot-swap ramp capacitor banks now have three adjacent capacitor pairs connected on both terminals. The CR_TOP branches use 0.35 mm front copper and the post-switch rail branches use 0.65 mm front copper. Each branch has continuous adjacent ground copper and uses no vias. KiCad verifies 6 pad-group joins and 1,025 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.65 | N_C49:2 to N_C45:2 | F.Cu | 6.38 |
| 0.65 | N_C22:2 to N_C21:2 | F.Cu | 6.38 |
| 0.65 | N_C45:2 to N_C42:2 | F.Cu | 7.29 |
| 0.35 | N_C49:1 to N_C45:1 | F.Cu | 5.64 |
| 0.35 | N_C22:1 to N_C21:1 | F.Cu | 5.64 |
| 0.35 | N_C45:1 to N_C42:1 | F.Cu | 5.43 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records the same 19 package-midline intersections as the previous board. [Whole-board survey](isolation-midlines.json)
