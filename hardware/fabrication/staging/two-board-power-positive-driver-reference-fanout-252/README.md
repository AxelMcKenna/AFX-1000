# Positive driver reference inputs

P_C32 feeds the two positive-regulator reference inputs at P_U5 pins 3 and 5. Both via transitions share the same adjacent In1 ground plane. The copper check verifies ground coverage along each trace outside its own drilled terminal clearances.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| PREF_FILTER | P_C32:1 and pin 3 via | In2.Cu | 13.95 |
| PREF_FILTER | P_U5:3 and pin 3 via | F.Cu | 0.80 |
| PREF_FILTER | pin 3 via and pin 5 via | In2.Cu | 6.11 |
| PREF_FILTER | P_U5:5 and pin 5 via | F.Cu | 1.98 |

 KiCad verified every expected pad group across the board. There are 943 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
