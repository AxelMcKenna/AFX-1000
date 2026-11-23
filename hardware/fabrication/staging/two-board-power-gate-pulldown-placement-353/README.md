# Gate pulldown placement

E_R2 and E_R26 are the 20 MΩ gate-to-source resistors for the positive 19 V and negative 12 V rail disconnects. Each resistor now sits on the MOSFET side of the board with separate front-layer connections to the gate and common-source pins. The four traces use no vias. [Measured placement and modeled clearances](component-placement.json)

KiCad verified 4 new connections and 764 remaining opens.

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /E_rail_disconnect/P19_GATE | E_R2:1, E_Q1:2 | F.Cu | 1.51 |
| /E_rail_disconnect/P19_COMMON | E_R2:2, E_Q1:1 | F.Cu | 4.19 |
| PWR_N12_BANK_GATE | E_R26:1, E_Q8:2 | F.Cu | 1.47 |
| PWR_N12_BANK_COMMON | E_R26:2, E_Q8:1 | F.Cu | 3.68 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
