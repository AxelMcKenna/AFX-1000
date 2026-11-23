# Negative 12 V supply branches

KiCad verified 3 new connections on PWR_N12_SOURCE. All branches use 0.80 mm traces over adjacent ground reference planes. The routes use existing lands and vias and add no drills. The power board has 800 remaining open connections.

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_N12_SOURCE | N_J4:1, N_C38:2 | In2.Cu | 6.46 |
| PWR_N12_SOURCE | N_R86:1, N_C38:2 | F.Cu | 21.09 |
| PWR_N12_SOURCE | N_C50:2, N_C51:2 | F.Cu | 26.33 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
