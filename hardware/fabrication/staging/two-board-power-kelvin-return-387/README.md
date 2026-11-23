# Converter input feed and undervoltage monitoring

Input capacitor P_C2 supplies inductor P_L1 through a 4.73 mm, 1.10 mm-wide front trace. A 13.59 mm, 1.20 mm-wide branch joins the inputs of P_L1 and P_L2. The 5 V digital source joins fan bypass capacitors F_C15 and F_C302 through 6.33 mm of 0.80 mm copper. The negative 12 V undervoltage sense trace connects M_R42:2 to comparator M_U2:9 over 32.41 mm. All four branches use front copper with no new vias. [Routing](layout.json) · [Ground and copper checks](plane-review.json)

KiCad verified four additional pad-group joins, leaving 701 open connections. Geometry and schematic parity checks pass. The paired placements match the enclosure capture and copper clears the surveyed isolation-package midlines. The power schematic retains two isolated-reference ERC warnings. [Connectivity](connectivity.json) · [DRC](drc.json) · [ERC](erc.json) · [Placement](placement.json) · [Isolation survey](isolation-midlines.json)
