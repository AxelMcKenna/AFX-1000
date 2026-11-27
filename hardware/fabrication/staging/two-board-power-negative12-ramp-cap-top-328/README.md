# Negative 12 V ramp capacitor connection

The 0.40 mm front-layer trace joins pin 1 of the 100 nF C0G ramp capacitors N_C44 and N_C43. It runs over continuous In1 ground with no added drills.

KiCad verified the intended join and 820 remaining open connections. The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /N_negative_startup_protection/N12_CR_TOP | N_C44:1, N_C43:1 | F.Cu | 10.22 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
