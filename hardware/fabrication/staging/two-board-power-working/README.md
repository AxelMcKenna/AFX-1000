# Power and protection PCB

KiCad verified 2 negative-rail sense connections. The board has 737 remaining opens. P_C14 now connects across both ends of P_R5. A separate trace connects P_R18 to the RAW_N22 capacitor group. Both sense branches are 0.30 mm wide and have continuous adjacent-layer analog ground. [Per-transition verification](plane-review.json)

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /P_power_supply/RAW_N22 | P_R18:2, P_C9:1 | B.Cu | 6.29 |
| /P_power_supply/RAW_N22 | P_R5:2, P_C14:1 | B.Cu | 4.06 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
