# Fan logic supply feed

The fan 3.3 V source now reaches pin 5 on F_U5, F_U11 and F_U14 as well as pin 1 on F_R24. Three front escapes and In2 branches share the In1 return. The source reaches 30 of its 31 assigned pads. Native refilling trimmed an additional 0.032 mm² of In6 ground near the vias. The ground islands remain connected, and that trim lies clear of existing signal traces and pads.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| V3V3 | F_U11:5 and branch via | F.Cu | 0.87 |
| V3V3 | branch via and f20e37e0-0c6b-5a6a-84e4-718762d35ef7 | In2.Cu | 8.21 |
| V3V3 | F_U5:5 and branch via | F.Cu | 0.49 |
| V3V3 | branch via and f20e37e0-0c6b-5a6a-84e4-718762d35ef7 | In2.Cu | 16.07 |
| V3V3 | F_R24:1 and branch via | F.Cu | 2.78 |
| V3V3 | branch via and 71a44371-123f-5a82-b74d-53fbb97d53d7 | In2.Cu | 19.05 |

 KiCad verified every expected pad group across the board. There are 936 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
