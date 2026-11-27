# Bias monitor reference resistor

M_R63 connects the 2.5 V monitor reference at M_R52 pin 1 to the NBIAS_R undervoltage threshold at M_R64 pin 1. Both front traces are 0.25 mm wide and share a continuous local In1 ground return tied to an existing via.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| REF_2V5 | M_R63:1 and M_R52:1 | F.Cu | 10.70 |
| NBIAS_R_UV_REF | M_R63:2 and M_R64:1 | F.Cu | 6.26 |

 KiCad verified every expected pad group across the board. There are 924 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
