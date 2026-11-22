# Analog output status routing

The E_R131 status network connects to E_U18 pin 14 through a 0.20 mm signal trace on F.Cu, In5.Cu and B.Cu. The middle layer runs over a continuous grounded In4 copper island. Both surface segments use their adjacent ground planes. KiCad verifies 1 pad-group joins and 1,073 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | E_R131:2 to E_U18:14 | F.Cu, In5.Cu, B.Cu | 47.04 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

The nearest ground vias connecting the two reference layers are 4.27 mm from the front-layer transition and 2.50 mm from the rear-layer transition.

[Projected clearances at isolation components](isolation-clearance.json)

The eight-layer survey records the same 46 package-midline intersections as the previous board. [Whole-board survey](isolation-midlines.json)

The two new vias increase the modeled In4 digital 5 V sheet resistance from the inductor to any of 18 load contacts by at most 0.025% across two mesh sizes. The maximum absolute increase is 0.0016 squares. [Digital rail calculations](digital-rail-sheet.json)
