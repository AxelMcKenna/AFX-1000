# Negative controller supply and ramp capacitor branches

KiCad verified 2 startup control connections. The board has 748 remaining opens. The 0.40 mm INTVCC supply branch and 0.20 mm ramp capacitor trace both have continuous reference copper. [Per-transition verification](plane-review.json)

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /N_negative_startup_protection/N19_CR_TOP | N_C19:1, N_C21:1 | F.Cu | 19.00 |
| /N_negative_startup_protection/N19_INTVCC | N_C7:1, N_C13:1 | In2.Cu | 22.01 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
