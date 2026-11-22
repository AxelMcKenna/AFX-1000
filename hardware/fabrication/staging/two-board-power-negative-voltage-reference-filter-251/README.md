# Negative voltage reference and RC filter

The two assigned LT1634 reference terminals and the bias and filter resistors connect on the rear copper. P_R19 feeds the 1 µF film capacitor P_C33. A local In6 ground pour provides a continuous return under the four new traces and joins the capacitor ground and two existing ground vias.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| NREF_FILTER | P_C33:1 and P_R19:2 | B.Cu | 9.34 |
| NREF_2V5 | P_U12:4 and P_U12:5 | B.Cu | 3.65 |
| NREF_2V5 | P_R18:1 and P_R19:1 | B.Cu | 3.25 |
| NREF_2V5 | P_U12:4 and P_R19:1 | B.Cu | 6.16 |

 KiCad verified every expected pad group across the board. There are 945 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
