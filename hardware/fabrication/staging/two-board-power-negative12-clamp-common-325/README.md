# Negative 12 V clamp common

The common output of the TLP4590AF photorelay N_U12 at pin 6 reaches pin 2 of N_J5. A 10.64 mm, 0.60 mm wide back-layer trace joins the two plated terminals with one 45-degree bend. The trace clears the photorelay input lands by at least 5.86 mm. The gate side of this clamp and selection of the physical interface remain open.

KiCad verified the intended join and 825 remaining open connections. The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_N12_BANK_COMMON | N_U12:6, N_J5:2 | B.Cu | 10.64 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
