# Negative 19 V rail enable

KiCad verified the enable connection between E_U2 pin 3 and E_R13 pin 1. The board has 778 remaining opens. The 0.20 mm signal traces reference ground along their length. At transitions that share a reference plane, the saved copper contains a continuous ground ring around the via. Where the reference changes, a nearby ground via joins the planes. [Per-transition verification](plane-review.json)

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /E_rail_disconnect/N19_ALLOW | E_U2:3, E_R13:1 | F.Cu, In2.Cu, B.Cu | 45.32 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
