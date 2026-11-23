# Analog reference and feedback branches

P_R46 joins P_C72 on the 1 V reference through 14.36 mm of copper. The raw positive regulator feedback connection from P_R3 to P_C12 uses 13.78 mm. Both branches stay on the back layer and are covered by analog ground on In6.Cu. The new ground copper preserves the existing supply fills and ground connections. [Routing](layout.json) · [Ground and copper checks](plane-review.json)

KiCad verified both pad-group joins, leaving 708 open connections. Geometry and schematic parity checks pass. The paired placements match the enclosure capture and copper clears the surveyed isolation-package midlines. The power schematic retains two isolated-reference ERC warnings. [Connectivity](connectivity.json) · [DRC](drc.json) · [ERC](erc.json) · [Placement](placement.json) · [Isolation survey](isolation-midlines.json)
