# Negative feedback divider midpoint

KiCad verified 1 feedback divider connection. The board has 743 remaining opens. P_R47 and P_R48 share a 0.20 mm back-layer trace. An extension of the inner analog-ground plane beneath the trace connects to the existing ground via beside the divider. [Per-transition verification](plane-review.json)

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /P_power_supply/LO_N_RMID | P_R47:2, P_R48:1 | B.Cu | 3.09 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
