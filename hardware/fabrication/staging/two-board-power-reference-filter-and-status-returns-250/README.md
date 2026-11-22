# Negative reference filter and validity header returns

The 1 µF film capacitor P_C33 returns directly to the negative 2.5 V reference P_U12 at pin 6. The NF output-valid header E_J12 returns to an existing ground via. Both ground traces are 0.60 mm wide. Native refilling preserved the existing copper pours.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| PWR_AGND | E_J12:2 and P_U12:6 | F.Cu | 7.56 |
| PWR_AGND | P_C33:2 and P_U12:6 | B.Cu | 8.21 |

 KiCad verified every expected pad group across the board. There are 949 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
