# Raw negative converter feedback capacitor

KiCad verified 1 feedback divider connection. The board has 742 remaining opens. A 0.20 mm back-layer trace joins the P_C14 feedback capacitor to the P_R4 pad group. The adjacent inner analog-ground plane covers the full trace width and connects to the existing ground via. [Per-transition verification](plane-review.json)

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /P_power_supply/RAW_N_FB | P_C14:2, P_R4:2 | B.Cu | 5.25 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
