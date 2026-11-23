# Flying capacitor and positive regulator feedback

P_R44 moved from (262.00, 120.00) mm to (273.05, 120.70) mm. Its feedback pad now connects to regulator P_U13:1 through 6.45 mm of front copper with a continuous ground reference. The RAW_P17 pad of P_R44 remains open. [Placement and clearance](component-placement.json)

Moving P_R44 made room for a 8.11 mm, 1.10 mm-wide front trace from flying capacitor P_C1:2 to Schottky diode P_D2:2. It clears nearby feedback, sense and reference copper by 4.78 mm in the front and adjacent inner layer survey. Both flying capacitor terminals now have connections. The P_L2:2 branch to the negative converter switch remains open. [Routing](layout.json) · [Ground and copper checks](plane-review.json)

KiCad verified two additional pad-group joins, leaving 699 open connections. Geometry and schematic parity checks pass. The paired placements match the enclosure capture and copper clears the surveyed isolation-package midlines. The power schematic retains two isolated-reference ERC warnings. [Connectivity](connectivity.json) · [DRC](drc.json) · [ERC](erc.json) · [Placement](placement.json) · [Isolation survey](isolation-midlines.json)
