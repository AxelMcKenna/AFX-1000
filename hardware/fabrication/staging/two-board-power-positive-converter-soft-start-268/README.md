# Positive converter soft start

P_R49 connects the 5 V digital source at P_R50 pin 1 to the LO_P_SS charging node at P_C74 pin 1. Both back traces are 0.25 mm wide and share a continuous local In6 ground return tied to an existing via.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| PWR_5V_DIG_SRC | P_R49:1 and P_R50:1 | B.Cu | 3.91 |
| LO_P_SS | P_R49:2 and P_C74:1 | B.Cu | 1.04 |

 KiCad verified every expected pad group across the board. There are 909 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
