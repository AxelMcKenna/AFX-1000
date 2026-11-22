# Negative 12 V converter secondary feed

The 15 V isolated converter N_U22 now feeds the 402 ohm resistor N_R73 from its positive secondary pin. The 8.28 mm front-layer trace runs at 45 degrees and stays on the output side of N_U22. N_C32 remains connected across secondary pins 4 and 6. The downstream resistor chain still requires routing.

KiCad verified the intended join and 843 remaining open connections. The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /N_negative_startup_protection/N12_ISO24 | N_U22:4, N_R73:1 | F.Cu | 8.28 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
