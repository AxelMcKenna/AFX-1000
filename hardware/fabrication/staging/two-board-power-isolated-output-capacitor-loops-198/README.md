# Isolated converter output capacitor loops

Each TMR1 isolated module connects directly to both lands of its local output capacitor. Each 0.40 mm rear-copper pair stays in the output domain and uses the dedicated floating return. Both pad-center loop areas are recorded in [output loops](output-loops.json). Converter startup, capacitive load and hot derating remain unqualified. KiCad verifies 4 pad-group joins and 1,055 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.40 | N_U17:4 to N_C5:1 | B.Cu | 2.08 |
| 0.40 | N_U17:6 to N_C5:2 | B.Cu | 2.16 |
| 0.40 | N_U22:4 to N_C32:1 | B.Cu | 2.08 |
| 0.40 | N_U22:6 to N_C32:2 | B.Cu | 2.16 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records the same 28 package-midline intersections as the previous board. [Whole-board survey](isolation-midlines.json)
