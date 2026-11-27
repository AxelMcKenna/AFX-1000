# Local protection monitor reference connections

Two short reference traces connect E_U18 pins 4 and 6 and pins 8 and 10. N_U18 and N_U23 each connect pin 11 (OV) to pin 13 (VEE) on their respective negative rail. All four traces have a continuous adjacent ground reference. KiCad verifies 4 pad-group joins and 1,202 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | E_U18:4 to E_U18:6 | B.Cu | 2.19 |
| 0.20 | E_U18:8 to E_U18:10 | B.Cu | 2.19 |
| 0.25 | N_U18:11 to N_U18:13 | F.Cu | 2.28 |
| 0.25 | N_U23:11 to N_U23:13 | F.Cu | 2.28 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
