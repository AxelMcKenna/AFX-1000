# Negative 12 V ramp capacitor returns

N_C41 and N_C44 now share the negative 12 V post-protection rail through a 2.08 mm straight trace between their adjacent lands. A 9.70 mm trace connects N_C44 to the existing N_C43 capacitor group. The front-layer traces are 0.50 mm and 0.75 mm wide, respectively. The capacitor bank still has open connections.

KiCad verified both intended joins and 826 remaining open connections. The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_N12_POST_NF | N_C41:2, N_C44:2 | F.Cu | 2.08 |
| PWR_N12_POST_NF | N_C44:2, N_C43:2 | F.Cu | 9.70 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
