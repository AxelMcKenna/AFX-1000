# Negative 19 V ramp capacitor source return

A 1.50 mm In3 trace ties the N_C26 and N_C27 return plane to the controller’s floating source network at an existing via. The timing terminals remain joined on In2. The controller RAMP pin still needs its signal connection.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| PWR_N19_SOURCE | N_C27:2 and N_R58:2 | In3.Cu | 37.69 |

 KiCad verified every expected pad group across the board. There are 932 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
