# Negative 12 V undervoltage reference

The reference resistor N_R50 pin 2 connects to N_U14 pin 6 through 7.65 mm of 0.25 mm copper and a 0.60 mm via with a 0.30 mm drill. The outer-layer traces have continuous adjacent analog ground outside the via clearance. An existing ground via contacts both reference planes. The signal via removes 0.7915 mm² from each of In1.Cu and In6.Cu.

KiCad confirms 1 intended pad-group join after refill, leaving 1,554 open connections. Geometry and schematic parity checks pass. ERC retains two isolated-reference warnings. The paired placement matches the assembly capture. All 953 via drills clear the plotted mask and paste openings.

[Routes](routes.json) · [Connectivity](connectivity.json) · [Plane measurements](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
