# Fan programming and monitoring connections

The three fan-control and programming connections use 0.25 mm traces. Each route stays over one continuous In1 ground island outside its own drilled terminal clearances. Native refill preserved all 245 zone shapes.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| ISP_MISO | F_U1:8 and F_J5:1 | F.Cu | 7.49 |
| MCU_RESET_N | F_R6:2 and F_J5:5 | F.Cu | 32.42 |
| FAN_R_TACH | F_U3:3 and F_J203:3 | In2.Cu | 51.08 |

 KiCad verified every expected pad group across the board. There are 957 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
