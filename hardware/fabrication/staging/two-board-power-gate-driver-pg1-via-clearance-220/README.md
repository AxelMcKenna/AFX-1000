# Gate-driver power-good via clearance at E_U2

The ANA_PG1 via and its two inner-layer traces now clear the E_U2 isolation midline. The old and new traces meet the same two fixed endpoints. Trace width, via drill and via land diameter are unchanged. Native refill checks verify the reference copper and every named pad group. KiCad verifies 0 pad-group joins and 1,014 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | E_U14:3 to E_U41:6 | In2.Cu, In6.Cu | 30.38 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records 11 package-midline intersections, one fewer than the previous board. [Whole-board survey](isolation-midlines.json)
