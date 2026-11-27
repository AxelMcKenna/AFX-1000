# Negative 12 V regulator output pins

A 0.50 mm front-layer trace connects LT3090 regulator P_U11 output pins 1 and 2. It is 0.30 mm wide at the DFN pads. A local inner ground-plane extension connects to an existing ground via beneath this route. KiCad verifies one intended pad-group join and 1,312 remaining connections. The regulator still needs its external output distribution and load testing.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.30 | P_U11:1 to P_U11:2 | F.Cu | 0.50 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
