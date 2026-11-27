# Fan tachometer pull-ups

F_R202 and F_R302 sit behind their respective fan headers. Each pull-up connects pin 2 (fan supply) to pin 3 (tachometer signal) through two 0.30 mm rear traces. The In6 ground return extends to the right header’s pin 1. The connector terminal clearances and modeled body envelopes are checked on the assembled pair.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| FAN_L_5V | F_R202:1 and F_J202:2 | B.Cu | 2.39 |
| FAN_L_TACH | F_R202:2 and F_J202:3 | B.Cu | 2.39 |
| FAN_R_5V | F_R302:1 and F_J203:2 | B.Cu | 2.39 |
| FAN_R_TACH | F_R302:2 and F_J203:3 | B.Cu | 2.39 |

 KiCad verified every expected pad group across the board. There are 926 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
