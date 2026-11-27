# Overvoltage reference divider

E_R89 pin 1 and E_R90 pin 1 share the REF_HIGH_AUX node. Their rear copper connection runs over a local In6 ground region tied to E_R89 pin 2 through the divider’s existing ground via. Both the new trace and the existing resistor return lie over this copper. Two further uninterrupted ground layers on In4 and In5 shield the divider from the 12 V inlet on In2 and In3. The source branch from E_R88 remains open.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| REF_HIGH_AUX | E_R89:1 and E_R90:1 | B.Cu | 3.21 |

 KiCad verified every expected pad group across the board. There are 930 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
