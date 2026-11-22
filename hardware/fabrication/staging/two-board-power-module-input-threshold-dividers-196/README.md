# Module input voltage dividers

G_R1 and G_R3 complete the local input connections of the TPS26601 undervoltage and overvoltage sense dividers. The two upper resistors share a sensing tap at G_U1 input pin 8. Their lower resistors connect to the dedicated RTN network. The four traces use front copper and add no vias. Energized trip points and the module feed still require verification. The modeled assembly clearances are recorded in [component placement](component-placement.json). KiCad verifies 4 pad-group joins and 1,061 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | G_R1:1 to G_U1:8 | F.Cu | 3.82 |
| 0.20 | G_R1:2 to G_U1:10 | F.Cu | 3.35 |
| 0.20 | G_R3:1 to G_R1:1 | F.Cu | 3.32 |
| 0.20 | G_R3:2 to G_R4:1 | F.Cu | 5.36 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records the same 28 package-midline intersections as the previous board. [Whole-board survey](isolation-midlines.json)
