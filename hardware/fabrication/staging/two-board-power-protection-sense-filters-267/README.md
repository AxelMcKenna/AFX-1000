# Rail monitoring and protection sense filters

The relocated capacitors connect to their sense-divider nodes through 0.25 mm copper. Each capacitor retains a local analog ground connection. Native KiCad verification checks all original zone fills and the ground coverage under both traces for every capacitor.

| Signal | Joined pad groups, representative pins | Layer | Length (mm) |
| --- | --- | --- | ---: |
| E28_ANA_SRC_SENSE | E_C53:1 and E_R123:2 | B.Cu | 2.17 |
| PWR_AGND | E_C53:2 and AGND via | B.Cu | 0.48 |
| E28_DIG_OUT_SENSE | E_C56:1 and E_R132:2 | F.Cu | 1.17 |
| PWR_AGND | E_C56:2 and AGND via | F.Cu | 0.42 |
| P12_OV_SENSE | M_C11:1 and M_R32:1 | F.Cu | 1.24 |
| PWR_AGND | M_C11:2 and AGND via | F.Cu | 0.71 |
| V5_REG_UV_SENSE | M_C25:1 and M_R75:1 | F.Cu | 1.21 |
| PWR_AGND | M_C25:2 and AGND via | F.Cu | 0.75 |
| 5V_DIG_UV_SENSE | M_C29:1 and M_R90:1 | F.Cu | 1.52 |
| PWR_AGND | M_C29:2 and AGND via | F.Cu | 0.42 |
| P19_OV_SENSE | M_C3:1 and M_R8:1 | F.Cu | 1.24 |
| PWR_AGND | M_C3:2 and M_R8:2 | F.Cu | 1.25 |
| 5V_DIG_UV_REF | M_C30:1 and M_R92:1 | B.Cu | 1.34 |
| PWR_AGND | M_C30:2 and E_R27:2 | B.Cu | 1.02 |

 KiCad verified every expected pad group across the board. There are 911 opens remaining.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
