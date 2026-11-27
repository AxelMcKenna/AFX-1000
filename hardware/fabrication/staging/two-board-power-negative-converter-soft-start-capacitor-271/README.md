# Negative converter soft-start capacitor

P_C76 connects to the negative converter soft-start resistor P_R50 through a 0.25 mm trace. The 4.84 mm charging trace connects the 5 V pads of P_R49 and P_R50 with two 45-degree bends. A dedicated ground via returns the capacitor to the adjacent analog ground copper. KiCad verified continuous ground copper under the capacitor connections and the rerouted supply trace. P_U13 pin 7 still needs a connection to this soft-start node.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| LO_N_SS | P_C76:1 and P_R50:2 | B.Cu | 1.02 |
| PWR_AGND | P_C76:2 and AGND via | B.Cu | 2.12 |

 KiCad verified every expected pad group across the board. There are 905 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
