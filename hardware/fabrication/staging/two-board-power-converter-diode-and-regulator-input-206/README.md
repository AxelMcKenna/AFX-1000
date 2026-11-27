# Converter diode and regulator input connections

P_C63 connects directly to the SS16 diode P_D4 through 1.00 mm front copper. On the LT3080, a 0.35 mm trace joins VCONTROL pin 5 to the raw input at pin 7. Both connections are shorter than 2.1 mm, have continuous adjacent ground copper, and use no vias. The switching and regulator circuits still have other open connections. KiCad verifies 2 pad-group joins and 1,049 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 1.00 | P_C63:2 to P_D4:2 | F.Cu | 2.00 |
| 0.35 | P_U7:5 to P_U7:7 | F.Cu | 1.89 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records the same 19 package-midline intersections as the previous board. [Whole-board survey](isolation-midlines.json)
