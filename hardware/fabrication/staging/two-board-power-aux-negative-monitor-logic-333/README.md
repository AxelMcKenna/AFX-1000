# Auxiliary supply for negative rail monitoring and logic

The 2.5 V auxiliary regulator now reaches 219 of 230 pads, up from 216. Each new branch is 0.40 mm wide and enters the existing supply group at the contact identified below. The adjacent ground planes and nearby ground vias were checked after refill. KiCad verified 2 supply joins and 809 remaining open connections.

The isolation survey found zero package-midline crossings.

| Net | Physical contacts | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_V2V5_AUX | N_U35 pin 14, existing auxiliary trace | F.Cu, In5.Cu, F.Cu | 10.85 |
| PWR_V2V5_AUX | N_U55 pin 5, N_U58 pin 5 | F.Cu, In5.Cu, F.Cu | 13.14 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
