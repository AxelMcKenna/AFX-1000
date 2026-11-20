# Module input eFuse package connections

On the TPS26601, 0.50 mm copper bridges the input pair and the output pair. Pin 15 (RTN) connects to its exposed pad on the module return net. Pin 17 retains its separate ground connection assignment. KiCad verifies 3 pad-group joins and 1,206 remaining connections. Module supply distribution, fault behavior and thermal performance still require verification.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.50 | G_U1:8 to G_U1:9 | F.Cu | 0.34 |
| 0.50 | G_U1:24 to G_U1:23 | F.Cu | 0.34 |
| 0.32 | G_U1:15 to G_U1:25 | F.Cu | 0.45 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
