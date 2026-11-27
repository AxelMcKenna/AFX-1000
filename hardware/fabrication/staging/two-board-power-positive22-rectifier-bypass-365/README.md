# Positive 22 V rectifier bypass

KiCad verified 2 capacitor connections. The board has 744 remaining opens. P_C7, the 100 nF bypass, sits opposite rectifier P_D1. Two short 0.40 mm rail traces share a through-via. A second through-via takes the capacitor return to analog ground. [Placement and clearances](component-placement.json) [Per-transition verification](plane-review.json)

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /P_power_supply/RAW_P22 | P_C7:1, P_D1:1 | F.Cu, B.Cu | 1.38 |
| PWR_AGND | P_C7:2, P_C5:2 | F.Cu | 0.91 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
