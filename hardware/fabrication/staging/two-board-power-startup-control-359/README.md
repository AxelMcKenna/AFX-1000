# Negative 19 V startup capacitor-bank control

KiCad verified 1 startup control connections. The board has 753 remaining opens. The 0.20 mm signal traces reference ground along their length. At transitions that share a reference plane, the saved copper contains a continuous ground ring around the via. Where the reference changes, a nearby ground via joins the planes. [Per-transition verification](plane-review.json)

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /N_negative_startup_protection/N19_CR_TOP | N_C19:1, N_C23:1 | In5.Cu | 9.66 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
