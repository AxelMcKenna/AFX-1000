# Negative converter and rail monitor

The Ćuk converter diode P_D2 connects to output inductor P_L3 through 8.31 mm of 1.20 mm front copper. Switch pin P_U1:6 connects to flying capacitor P_C1 through 3.80 mm of front copper, widening from 0.27 mm at the pin to 0.65 mm. The capacitor-to-diode branch remains open. The negative overvoltage sense connection between M_R19 and M_U1 follows 23.50 mm of front copper with continuous analog ground underneath. All three branches are via-free. [Routing](layout.json) · [Ground and copper checks](plane-review.json)

KiCad verified three pad-group joins, leaving 705 open connections. Geometry and schematic parity checks pass. The paired placements match the enclosure capture and copper clears the surveyed isolation-package midlines. The power schematic retains two isolated-reference ERC warnings. [Connectivity](connectivity.json) · [DRC](drc.json) · [ERC](erc.json) · [Placement](placement.json) · [Isolation survey](isolation-midlines.json)
