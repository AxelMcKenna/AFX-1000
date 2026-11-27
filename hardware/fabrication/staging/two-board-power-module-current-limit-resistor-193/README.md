# Module current-limit resistor

The TPS26601 current-limit resistor G_R5 connects directly to G_U1 pin 19 (ILIM) and pin 15 (RTN). The two front-layer traces use the controller's dedicated return and add no vias. Closing their endpoints across the resistor and the IC gives a projected loop area of 2.14 mm². The native refill preserves every existing plane polygon. The modeled assembly clearances are recorded in [component placement](component-placement.json). KiCad verifies 2 pad-group joins and 1,069 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | G_R5:1 to G_U1:19 | F.Cu | 1.25 |
| 0.20 | G_R5:2 to G_U1:15 | F.Cu | 4.22 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records the same 38 package-midline intersections as the previous board. [Whole-board survey](isolation-midlines.json)
