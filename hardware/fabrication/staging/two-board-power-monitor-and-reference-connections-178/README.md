# Monitor supply and reference connections

The table records the new branches and their copper widths. Each segment has an adjacent ground return checked after the copper refill. KiCad verifies 14 pad-group joins and 1,092 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.40 | M_R13:1 to M_R18:1 | F.Cu | 27.16 |
| 0.40 | E_R87:1 to E_R82:1 | B.Cu | 10.67 |
| 0.20 | P_U6:6 to P_R40:2 | B.Cu | 4.98 |
| 0.20 | P_R310:1 to P_U25:10 | F.Cu, B.Cu | 3.97 |
| 0.20 | E_U10:13 to E_R92:2 | F.Cu, B.Cu | 4.36 |
| 0.20 | P_C243:1 to P_C249:1 | F.Cu, B.Cu | 6.61 |
| 0.20 | E_R129:2 to E_U18:9 | F.Cu, B.Cu | 8.27 |
| 0.20 | E_U11:9 to E_U37:5 | F.Cu, B.Cu | 12.35 |
| 0.20 | P_R240:2 to P_C250:1 | B.Cu, In3.Cu | 6.49 |
| 0.40 | E_C13:1 to E_U3:1 | F.Cu | 14.36 |
| 0.40 | E_U4:1 to E_R88:1 | F.Cu | 7.72 |
| 0.40 | E_C38:1 to E_C70:1 | F.Cu, B.Cu | 17.37 |
| 0.40 | P_C401:1 to N_U7:8 | B.Cu, F.Cu | 14.49 |
| 0.20 | E_U10:10 to E_R94:1 | F.Cu, B.Cu | 2.92 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

The added copper clears the projected land envelopes of all eight negative-startup isolation packages. [Measured distances](isolation-clearance.json)

The largest modeled change in per-layer resistance between the inlet and source vias was 0.021% across the two mesh settings. The model uses ideal contacts. Copper thickness and thermal performance still require qualification. [Inlet-plane calculation](inlet-sheet-comparison.json)
