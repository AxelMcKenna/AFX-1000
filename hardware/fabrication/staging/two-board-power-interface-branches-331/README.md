# Fan programmer clock and rail disconnect common

The fan-controller ISP clock runs from header F_J5 pin 3 to F_U1 pin 9. The positive 12 V disconnect driver common runs from E_U3 pin 5 to E_R18 pin 2. Each connection uses one 0.60 mm via with a 0.30 mm drill. KiCad verified both pad-group joins and 816 remaining open connections. The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /E_rail_disconnect/P12_COMMON | E_U3:5, E_R18:2 | F.Cu, B.Cu | 6.26 |
| /F_fan_health_protection/ISP_SCK | F_J5:3, F_U1:9 | In5.Cu, F.Cu | 11.37 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
