# Eight-layer clearance at N_U11

Five keepouts extend the three existing inner-layer rules at N_U11 to all eight copper layers. Each layer excludes tracks, vias, pads and pours from a 3.40 mm strip between the contact banks. The pre-existing In1 strip has a 0.20 mm offset. Native polygon intersection verifies a common 3.20 mm by 7.12 mm copper-free rectangle through the stack. The eight-layer survey records 21 midline crossings, down from 22. Other packages still have crossings. Installed insulation performance and fabrication qualification remain open.

| Package | Copper layer | Width (mm) | Length (mm) |
|---|---|---:|---:|
| N_U11 | F.Cu | 3.40 | 7.12 |
| N_U11 | B.Cu | 3.40 | 7.12 |
| N_U11 | In2.Cu | 3.40 | 7.12 |
| N_U11 | In3.Cu | 3.40 | 7.12 |
| N_U11 | In6.Cu | 3.40 | 7.12 |

The regenerated ground polygons retain their island counts. Existing tracks retain the adjacent reference copper checked in the fill review. Every named pad group matches revision 202, with 1,053 opens.

[Keepout](isolation-rule.json) · [Filled copper](plane-review.json) · [Isolation survey](isolation-midlines.json) · [Connectivity](connectivity.json) · [DRC](drc.json) · [ERC](erc.json)
