# Panel switch ground return

KiCad verified 1 panel switch ground connection. The board has 747 remaining opens. A 0.40 mm front-layer trace connects switch pin 3 directly to ground on panel header I_J1 pin 2. [Per-transition verification](plane-review.json)

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_AGND | I_S1:3, I_J1:2 | F.Cu | 11.81 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
