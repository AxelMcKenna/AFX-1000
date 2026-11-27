# Gate driver primary-side auxiliary supply

The N_U22 DC/DC converter now has a 2.13 mm copper keepout between its input and output lands on all eight layers. The filled-copper and ground-return checks are recorded in the plane review. The table records the new supply branches. Each segment has an adjacent ground return checked after the copper refill. KiCad verifies 1 pad-group joins and 1,082 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.40 | E_U4:1 to E_C13:1 | F.Cu | 16.93 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

The new copper stays on the input side at its gate-driver terminals. The projected clearance report includes 13 isolation packages. [Measured distances](isolation-clearance.json)

The N_U22 keepout clears its isolation midline on all eight copper layers. The survey records 69 remaining layer intersections across the board. E_U3 still needs a primary-side supply connection. [Whole-board survey](isolation-midlines.json)
