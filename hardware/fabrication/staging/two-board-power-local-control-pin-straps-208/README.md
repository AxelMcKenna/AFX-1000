# Local control-pin straps

Front-layer traces join the 5 V supply straps at F_U2 and F_U8 and the local source-net straps at both negative hot-swap controllers. All four traces have continuous adjacent ground copper and use no vias. KiCad verifies 4 pad-group joins and 1,041 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.25 | F_U2:5 to F_U2:8 | F.Cu | 2.53 |
| 0.25 | F_U8:2 to F_U8:8 | F.Cu | 5.08 |
| 0.25 | N_U18:1 to N_U18:3 | F.Cu | 1.86 |
| 0.25 | N_U23:1 to N_U23:3 | F.Cu | 1.86 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records the same 19 package-midline intersections as the previous board. [Whole-board survey](isolation-midlines.json)
