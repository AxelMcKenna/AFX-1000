# Negative rail ramp capacitor bank

KiCad verified 5 connections and 787 remaining opens. The 0.40 mm ramp capacitor traces reference ground along their length. At transitions that share a reference plane, the saved copper contains a continuous ground ring around the via. Where the reference changes, a nearby ground via joins the planes. [Per-transition verification](plane-review.json)

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /N_negative_startup_protection/N19_CR_TOP | N_C16:1, N_C19:1 | F.Cu, In2.Cu, F.Cu | 11.09 |
| /N_negative_startup_protection/N19_CR_TOP | N_C14:1, N_C15:1 | F.Cu, In2.Cu, F.Cu | 12.79 |
| /N_negative_startup_protection/N19_CR_TOP | N_C25:1, N_C19:1 | F.Cu, In5.Cu, F.Cu | 24.10 |
| /N_negative_startup_protection/N19_CR_TOP | N_C15:1, N_C24:1 | F.Cu, In5.Cu, F.Cu | 25.57 |
| /N_negative_startup_protection/N19_CR_TOP | N_C14:1, N_C23:1 | F.Cu, In2.Cu, F.Cu, In2.Cu, F.Cu | 38.53 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
