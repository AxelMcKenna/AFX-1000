# Fan protection current-limit resistor placement

F_R401 connects the current-limit pin of F_U401 to system ground. The resistor sits on the rear face, with one signal via and a short return to an existing ground via. The modeled assembly clearances are recorded in [component placement](component-placement.json). KiCad verifies 2 pad-group joins and 1,090 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | F_R401:1 to F_U401:5 | B.Cu, F.Cu | 5.24 |
| 0.20 | F_R401:2 to P_C103:2 | B.Cu | 2.11 |

Two inherited auxiliary-supply traces cross the midpoint between the input and output pin rows at E_U3 and E_U4. Their nearest isolated lands are 0.343 mm and 0.363 mm away. Both require rerouting before fabrication. [Gate-driver isolation review](gate-driver-isolation-review.json)

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

The whole-board survey found copper at the midpoint between the two pin banks of 13 isolation packages. The 75 layer intersections include 50 filled-plane intersections. The record identifies each layer, net and object for layout review. Installed isolation remains unverified. [Copper intersections by package](isolation-midlines.json)
