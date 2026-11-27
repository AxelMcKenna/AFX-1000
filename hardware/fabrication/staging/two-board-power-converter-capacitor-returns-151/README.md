# Converter capacitor and feedback returns

Ten converter capacitors have 0.60 mm rear-layer returns to the system-ground plane. The reference bypass P_C11, soft-start capacitor P_C13 and feedback resistor P_R3 use 0.30 mm returns. Each return has a separate 0.60/0.30 mm via into the existing In1.Cu ground copper. Converter ripple, regulation and thermal performance still require measurement. KiCad verifies 13 pad-group joins and 1,180 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.60 | P_C4:2 to P_C103:2 | B.Cu | 1.74 |
| 0.60 | P_C68:2 to P_C103:2 | B.Cu | 0.77 |
| 0.60 | P_C56:2 to P_C103:2 | B.Cu | 0.77 |
| 0.60 | P_C61:2 to P_C103:2 | B.Cu | 0.77 |
| 0.60 | P_C64:2 to P_C103:2 | B.Cu | 1.82 |
| 0.60 | P_C8:2 to P_C103:2 | B.Cu | 1.87 |
| 0.60 | P_C62:2 to P_C103:2 | B.Cu | 2.12 |
| 0.60 | P_C6:2 to P_C103:2 | B.Cu | 0.77 |
| 0.60 | P_C67:2 to P_C103:2 | B.Cu | 0.77 |
| 0.60 | P_C70:2 to P_C103:2 | B.Cu | 0.77 |
| 0.30 | P_R3:2 to P_C103:2 | B.Cu | 0.69 |
| 0.30 | P_C13:2 to P_C103:2 | B.Cu | 0.69 |
| 0.30 | P_C11:2 to P_C103:2 | B.Cu | 0.69 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
