# Capacitor and protection diode ground returns

P_C5 pin 2, the RAW_P22 output capacitor return, joins the input capacitor P_C3 ground pad through 3.60 mm of 1.00 mm front-layer copper. P_D103 pin 2 joins a row of three existing ground vias near the input protection diodes through 6.32 mm of 1.50 mm bottom copper. KiCad verified two ground-group joins, with 839 open connections remaining. Transient performance still requires hardware testing.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_AGND | P_C5:2, P_C3:2 | F.Cu | 3.60 |
| PWR_AGND | P_D103:2, P_D101:2 | B.Cu | 6.32 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
