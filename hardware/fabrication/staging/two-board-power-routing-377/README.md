# Negative-rail monitor bias network

All four assigned resistor pads reach the monitor bias node. The front trace connects P_R310 to P_R311 and P_R312. P_R314 connects to P_R312 through a single 0.30 mm drill. Their front and back traces total 17.57 mm. The ground via 2.78 mm from that layer change connects both reference planes. Ground copper covers both traces up to the signal via clearance. [Route geometry](layout.json) · [Reference-plane verification](plane-review.json)

KiCad counted 721 remaining opens and preserved every other pad group. All eight layers refill reproducibly. The power and signal placements match the enclosure capture, and copper clears the surveyed isolation-package midlines. Two ground-pin ERC warnings remain. [Connectivity](connectivity.json) · [Placement](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
