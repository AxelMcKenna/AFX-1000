# Fan logic supply

The 0.25 mm front trace joins pin 5 of the fan Schmitt buffer F_U11 and pin 5 of the open-drain inverter F_U14. Continuous ground on In1 supports this branch. Both pins still need a feed from the 3.3 V source.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| V3V3 | F_U14:5 and F_U11:5 | F.Cu | 14.94 |

 KiCad verified every expected pad group across the board. There are 939 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
