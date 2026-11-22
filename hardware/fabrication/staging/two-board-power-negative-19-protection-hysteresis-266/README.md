# Negative 19 V overvoltage hysteresis

E_R63 closes the hysteresis feedback branch between E_U9 pin 1 and its negative 19 V overvoltage threshold at pin 7. Both front traces are 0.25 mm wide and share a continuous local In1 ground return tied to an existing via.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| PWR_N19_OV_OK | E_R63:1 and E_U9:1 | F.Cu | 5.48 |
| N19_OV_REF | E_R63:2 and E_U9:7 | F.Cu | 13.42 |

 KiCad verified every expected pad group across the board. There are 918 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
