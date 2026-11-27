# Regulated 5 V overvoltage monitor filter

M_C27 connects to the sense divider at M_R82 through a 0.25 mm trace. A second trace connects the capacitor to analog ground. KiCad verified continuous ground copper under both traces.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| V5_REG_OV_SENSE | M_C27:1 and M_R82:1 | B.Cu | 1.67 |
| PWR_AGND | M_C27:2 and M_C30:2 | B.Cu | 4.33 |

 KiCad verified every expected pad group across the board. There are 906 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
