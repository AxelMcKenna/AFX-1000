# Converter input bypass loops

Each TMR1 isolated module connects directly to both lands of its local input bypass capacitor. Each 0.65 mm rear-copper pair joins the positive 12 V module feed and its input return. Both pad-center loop areas are recorded in [input loops](input-loops.json). Converter startup, capacitive load and hot derating remain unqualified. KiCad verifies 4 pad-group joins and 1,045 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.65 | N_U17:2 to N_C4:1 | B.Cu | 2.27 |
| 0.65 | N_U17:1 to N_C4:2 | B.Cu | 2.26 |
| 0.65 | N_U22:2 to N_C31:1 | B.Cu | 2.27 |
| 0.65 | N_U22:1 to N_C31:2 | B.Cu | 2.26 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records the same 19 package-midline intersections as the previous board. [Whole-board survey](isolation-midlines.json)
