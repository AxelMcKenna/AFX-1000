# Negative-rail monitor bias network

P_R310 pad 2 now connects to P_R311 pad 1 and P_R312 pad 1. The 13.19 mm trace runs on the front layer. A local ground-plane extension on In1.Cu covers the full trace and connects to the existing ground via at (318.1617, 115.5752) mm. P_R314 still needs its connection to this network. [Route geometry](layout.json) · [Ground plane measurements](plane-review.json)

KiCad counted 722 remaining opens and verified that every other pad group was preserved. All eight copper layers refill reproducibly. The signal and power placements match the enclosure capture. The isolation survey found zero package-midline crossings. The power schematic retains two ground-pin ERC warnings. [Connectivity](connectivity.json) · [Placement](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
