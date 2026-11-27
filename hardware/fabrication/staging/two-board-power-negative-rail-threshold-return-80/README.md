# Negative rail threshold reference return

A 0.98 mm rear-layer trace joins N_R35 pin 2 to the main ground plane through a 0.60 mm via with a 0.30 mm drill. This resistor forms part of the negative 19 V source undervoltage reference. The plane review and native connectivity checks cover the complete trace and via.

KiCad confirms one intended pad-group join and 1,403 remaining open connections. Geometry and schematic parity pass. ERC retains the two isolated-reference warnings. Both PCB placements match the assembly capture.

[Route](routes.json) · [Connectivity](connectivity.json) · [Ground plane changes](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
