# Negative rail monitor divider ground return

KiCad verified 1 monitor divider ground connection. The board has 746 remaining opens. A 0.25 mm front-layer trace connects the grounded ends of M_R47 and M_R26. Both resistors belong to the rail monitor. [Per-transition verification](plane-review.json)

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_AGND | M_R47:2, M_R26:2 | F.Cu | 18.98 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
