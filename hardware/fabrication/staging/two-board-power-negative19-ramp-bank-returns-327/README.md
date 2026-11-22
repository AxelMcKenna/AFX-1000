# Negative 19 V ramp capacitor bank returns

Two 0.40 mm front-layer branches connect ramp capacitor returns on PWR_N19_POST_NF. One joins N_C25 pin 2 to existing copper connected to N_C19 pin 2. The second joins N_C22 pin 2, already connected to N_C21 pin 2, to the drain land of N_Q1. Both run over the In1 ground plane. They clear primary module feed and return copper by at least 4.10 mm and 16.80 mm respectively in projection across all layers.

KiCad verified both intended joins and 821 remaining open connections. The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_N19_POST_NF | N_C25:2, N_C19:2 | F.Cu | 17.92 |
| PWR_N19_POST_NF | N_C21:2, N_Q1:2 | F.Cu | 13.55 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
