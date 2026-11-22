# Positive voltage reference and filter resistor

P_R17 moves to the rear between the positive 2.5 V reference and its film capacitor. The two 0.25 mm traces connect the reference output to P_R17 and P_R17 to P_C32. The filtered voltage now reaches P_U5 pins 3 and 5. Both new traces share a continuous In6 ground region outside the film capacitor's own plated-hole clearance.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| PREF_2V5 | P_R17:1 and P_C31:1 | B.Cu | 4.06 |
| PREF_FILTER | P_R17:2 and P_C32:1 | B.Cu | 6.89 |

 KiCad verified every expected pad group across the board. There are 941 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
