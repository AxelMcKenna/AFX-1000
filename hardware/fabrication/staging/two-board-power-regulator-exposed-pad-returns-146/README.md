# Converter exposed-pad returns

Two 0.60 mm front-layer traces connect P_U13's exposed pad and the P_D4 rectifier cathode to separate 0.60/0.30 mm vias. Both traces clear the FB2N land. Both vias land in the existing In1.Cu system-ground plane. Pin 5 shares this return through its short connection to the exposed pad. KiCad verifies 2 pad-group joins and 1,200 remaining connections. Converter thermal performance and switching noise still require measurement.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.60 | P_U13:11 to P_C103:2 | F.Cu | 3.21 |
| 0.60 | P_U13:11 to P_C103:2 | F.Cu | 4.37 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
