# Negative source load resistor return

P_R38 is the 9.09 kΩ load across the −19 V source and analog ground. Its nominal load current is 2.09 mA. A 2.24 mm trace, 0.30 mm wide, connects pad 2 to the main ground plane through a 0.60 mm via with a 0.30 mm drill. The plane review and native connectivity checks cover the complete trace and via.

KiCad confirms one intended pad-group join and 1,424 remaining open connections. Geometry and schematic parity pass. ERC retains the two isolated-reference warnings. Both PCB placements match the assembly capture.

[Route](routes.json) · [Connectivity](connectivity.json) · [Ground plane changes](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
