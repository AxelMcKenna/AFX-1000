# Negative raw converter feedback divider

P_R5 connects the RAW_N22 output capacitor P_C9 to the feedback divider at P_R4. The high-impedance junction uses the shorter of the two traces. Both back traces are 0.25 mm wide and share a continuous local In6 ground return tied to an existing via.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| RAW_N_FB | P_R5:1 and P_R4:2 | B.Cu | 2.21 |
| RAW_N22 | P_R5:2 and P_C9:1 | B.Cu | 9.90 |

 KiCad verified every expected pad group across the board. There are 922 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
