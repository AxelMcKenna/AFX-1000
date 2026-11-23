# Converter input bypass

The LT3471 input pin P_U1:8 connects to its 100 nF bypass capacitor P_C4:1 through 3.20 mm of copper. A 0.30 mm drill joins the 0.32 mm front trace to the 0.50 mm back trace. A ground via 1.51 mm away connects the two reference planes. Both traces retain ground coverage outside the power via clearance. [Routing](layout.json) · [Ground and copper checks](plane-review.json)

KiCad verified the input-to-capacitor join, leaving 697 open connections. Geometry and schematic parity checks pass. The paired placements match the enclosure capture and copper clears the surveyed isolation-package midlines. The power schematic retains two isolated-reference ERC warnings. [Connectivity](connectivity.json) · [DRC](drc.json) · [ERC](erc.json) · [Placement](placement.json) · [Isolation survey](isolation-midlines.json)
