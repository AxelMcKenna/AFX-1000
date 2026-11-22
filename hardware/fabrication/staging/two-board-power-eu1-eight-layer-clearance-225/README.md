# Eight-layer clearance at E_U1

Eight keepouts protect the space between the contact banks at E_U1. Native polygon intersection verifies a common 1.80 mm by 4.85 mm rectangle free of pads, tracks, vias and pours between the contact banks. The eight-layer survey records 0 midline crossings, down from 2. Installed insulation performance and fabrication qualification remain open.

| Package | Copper layer | Width (mm) | Length (mm) |
|---|---|---:|---:|
| E_U1 | F.Cu | 1.80 | 4.85 |
| E_U1 | In1.Cu | 2.10 | 4.85 |
| E_U1 | In2.Cu | 2.50 | 4.85 |
| E_U1 | In3.Cu | 2.50 | 4.85 |
| E_U1 | In4.Cu | 2.50 | 4.85 |
| E_U1 | In5.Cu | 1.80 | 4.85 |
| E_U1 | In6.Cu | 1.80 | 4.85 |
| E_U1 | B.Cu | 1.80 | 4.85 |

Opening the ground plane beside the isolated output bank removes 9.34 mm² beyond the 0.25 mm keepout collar on In6, including 0.25 mm² beneath the ground pad of E_R101. Its 1.13 mm back-layer trace still reaches the main ground network through the existing via. Every ground pad and via retains its checked plane contact. [Ground-return check](isolated-side-ground.json)

The filled inlet-plane copper matches revision 224 on both layers. The regenerated ground polygons retain their island counts. Existing tracks retain the adjacent reference copper checked in the fill review. Every named pad group matches revision 224, with 1,011 opens.

[Keepout](isolation-rule.json) · [Filled copper](plane-review.json) · [Isolation survey](isolation-midlines.json) · [Connectivity](connectivity.json) · [DRC](drc.json) · [ERC](erc.json)
