# Negative rail ramp series connections

The 39 Ω resistor N_R89 connects to N_C50 on N12_RAMP, and the 27 Ω resistor N_R72 connects to N_C27 on N19_RAMP. Both resistors now connect to their capacitor banks on both terminals. Each new 0.40 mm branch uses a single 0.60 mm via with a 0.30 mm drill. KiCad verified both intended joins and 795 remaining open connections.

On In5, the KiCad refill rounded the ground edge beside the −12 V route. The affected ground zone retained one connected region. Comparison against the previous board found no loss of reference copper under existing adjacent pads or traces. The isolation survey found zero package-midline crossings.

| Net | Physical contacts | Layer | Length (mm) |
| --- | --- | --- | --- |
| /N_negative_startup_protection/N12_RAMP | N_R89 pin 1, N_C50 pin 1 | F.Cu, In5.Cu | 20.01 |
| /N_negative_startup_protection/N19_RAMP | N_C27 pin 1, N_R72 pin 1 | In5.Cu, F.Cu | 25.50 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
