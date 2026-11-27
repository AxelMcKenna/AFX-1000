# Negative 12 V protection threshold divider

E_R70 connects the protection reference at E_R62 to the negative 12 V overvoltage threshold at E_R71. Both back traces are 0.25 mm wide and share a continuous local In6 ground return tied to an existing via.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| PWR_PROTECT_REF | E_R70:1 and E_R62:1 | B.Cu | 1.69 |
| N12_OV_REF | E_R70:2 and E_R71:2 | B.Cu | 11.75 |

 KiCad verified every expected pad group across the board. There are 920 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
