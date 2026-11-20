# Converter exposed-pad returns

Two 0.60 mm front-layer traces connect P_U1's exposed pad to separate 0.60/0.30 mm vias. Both vias land in the existing In1.Cu system-ground plane. Pin 5 shares the local return. Each via passes through the 12 V module-feed plane with a conventional clearance opening. The openings preserve the plane islands and clear the projected traces on both adjacent layers. KiCad verifies 1 pad-group join and 1,199 remaining connections. Converter thermal performance and switching noise still require measurement.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.60 | P_U1:11 to P_C103:2 | F.Cu | 2.02 |
| 0.60 | P_U1:11 to P_C103:2 | F.Cu | 1.95 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
