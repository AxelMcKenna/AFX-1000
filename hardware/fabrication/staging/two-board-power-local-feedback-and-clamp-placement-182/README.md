# Local feedback and clamp resistor placement

N_R98 shunts the input pins of optical relay N_U6. The branches stay on the LED side of the relay. E_R91 connects the reference comparator E_U10 output to its positive input through a local feedback resistor. The modeled assembly clearances are recorded in [component placement](component-placement.json). KiCad verifies 4 pad-group joins and 1,078 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | N_R98:1 to N_U6:1 | B.Cu | 0.79 |
| 0.20 | N_R98:2 to N_U6:2 | B.Cu | 6.90 |
| 0.20 | E_R91:1 to E_U10:13 | B.Cu, F.Cu | 2.53 |
| 0.20 | E_R91:2 to E_U10:11 | B.Cu, F.Cu | 1.74 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records the same 69 package-midline intersections as the previous board. [Whole-board survey](isolation-midlines.json)
