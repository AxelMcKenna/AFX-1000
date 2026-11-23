# Rail protection status

KiCad verified 2 rail-protection status connections. The board has 768 remaining opens. The 0.20 mm signal traces reference ground along their length. At transitions that share a reference plane, the saved copper contains a continuous ground ring around the via. Where the reference changes, a nearby ground via joins the planes. [Per-transition verification](plane-review.json)

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /E_rail_disconnect/E28_OUT_ARMED | E_U26:1, E_U22:4 | B.Cu, In5.Cu, B.Cu | 22.11 |
| /N_negative_startup_protection/N12_BIAS_RESET_N | N_U24:3, N_U25:6 | F.Cu, In2.Cu, F.Cu | 44.13 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
