# Source reset and auxiliary monitor

The 0.20 mm AX03_SOURCE_RESET trace connects P_R401 pin 2 to P_U201 pin 6 over 35.46 mm. OK_AUXILIARY connects E_U12 pins 6 and 10 over 9.04 mm. Both connections use existing component placements and outer-layer copper. The native refill confirms continuous ground beneath both traces and preserves all previous filled areas.

KiCad confirms two intended pad-group joins and 1,458 remaining open connections. Geometry and schematic parity pass. ERC retains the two isolated-reference warnings. Both PCB placements match the assembly capture.

[Route](routes.json) · [Connectivity](connectivity.json) · [Ground plane changes](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
