# Rail monitor feedback placement

M_R37 connects the M_U2 overvoltage comparator output and positive input. Its two traces run beside the comparator on the rear copper layer. The modeled assembly clearances are recorded in [component placement](component-placement.json). KiCad verifies 2 pad-group joins and 1,074 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | M_R37:1 to M_U2:1 | B.Cu, F.Cu | 4.16 |
| 0.20 | M_R37:2 to M_U2:7 | B.Cu, F.Cu | 3.51 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

[Projected clearances at isolation components](isolation-clearance.json)

The maximum modeled change in inlet-plane sheet resistance was 0.178%. [Mesh calculations](inlet-sheet-comparison.json)

The eight-layer survey records the same 48 package-midline intersections as the previous board. [Whole-board survey](isolation-midlines.json)

The two new vias increase the modeled In4 digital 5 V sheet resistance from the inductor to any of 18 load contacts by at most 1.277% across two mesh sizes. The maximum absolute increase is 0.0746 squares. [Digital rail calculations](digital-rail-sheet.json)
