# Positive rail source connections

E_J1 pin 1 reaches the 19 V rail disconnect MOSFET E_Q1 pin 3 through 5.08 mm of 1.00 mm front copper. P_J2 pin 6 reaches LT3045 regulator P_U22 pin 10 through 5.72 mm of 0.55 mm front copper. Both routes stay over the existing In1 ground plane outside terminal clearances and use no vias.

KiCad verified both intended joins and 829 remaining open connections. The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_P19_SRC | E_Q1:3, E_J1:1 | F.Cu | 5.08 |
| PWR_V5_REG_SRC | P_U22:10, P_J2:6 | F.Cu | 5.72 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
