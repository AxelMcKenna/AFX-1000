# Power-good trace clearance at E_U1

ANA_PG0 passes around the E_U1 isolation gap on In3 and F.Cu. The 30.09 mm route replaces 13.73 mm of In6 copper, retains both plated endpoints and adds one 0.60 mm via with a 0.30 mm drill. The return-path review checks the In4 and In1 ground copper. KiCad verifies 0 pad-group joins and 1,011 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | E_U13:3 to E_U41:3 | In3.Cu, F.Cu | 30.09 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The maximum modeled change in inlet-plane sheet resistance was 0.362%. [Mesh calculations](inlet-sheet-comparison.json)

The eight-layer survey records 2 package-midline intersections, one fewer than the previous board. [Whole-board survey](isolation-midlines.json)
