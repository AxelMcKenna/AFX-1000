# Converter timing and reference capacitors

The relocated capacitors connect to their timing or reference nodes through 0.25 mm copper. Each capacitor retains a local analog ground connection. The previous P_C13 ground via was retired with its only trace. KiCad verifies the local ground copper under both traces for each capacitor.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| SW_REF_1V | P_C11:1 and P_R4:1 | B.Cu | 1.06 |
| PWR_AGND | P_C11:2 and AGND via | B.Cu | 0.63 |
| RAW_P_SS | P_C13:1 and P_R6:2 | B.Cu | 1.52 |
| PWR_AGND | P_C13:2 and AGND via | B.Cu | 0.39 |

 KiCad verified every expected pad group across the board. There are 907 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
