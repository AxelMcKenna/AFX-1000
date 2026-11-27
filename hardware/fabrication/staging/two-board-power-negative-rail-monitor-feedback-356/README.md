# Negative 19 V output monitor feedback

KiCad verified 1 monitor feedback connections. The board has 760 remaining opens. The 0.20 mm signal traces reference ground along their length. At transitions that share a reference plane, the saved copper contains a continuous ground ring around the via. Where the reference changes, a nearby ground via joins the planes. [Per-transition verification](plane-review.json)

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /N_negative_startup_protection/N19_OUT_INV | N_R32:1, N_R24:1 | B.Cu, In2.Cu, F.Cu | 13.91 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
