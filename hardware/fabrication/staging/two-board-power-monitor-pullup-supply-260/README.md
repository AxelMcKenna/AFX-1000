# Rail monitor pull-up supply

A 0.30 mm front trace joins the supply side of M_R24 and M_R55 to the group containing M_R6, M_R13, M_R18 and M_R72. These six pull-ups still need a connection to the 3.3 V source. In1 analog ground underlies the full trace, with 0.86 mm minimum clearance to a ground-field edge. The grounded shield separates it from the 12 V inlet on In2 and In3. Native refilling left all plane fills unchanged.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| V3V3_IO | M_R13:1 and M_R55:1 | F.Cu | 16.45 |

 KiCad verified every expected pad group across the board. There are 931 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
