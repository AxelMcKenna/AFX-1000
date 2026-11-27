# Auxiliary rail branches for six additional loads

Six 0.40 mm surface branches connect E_U9, E_U10, E_R64, E_R92, E_R61 and N_C59 to the auxiliary regulator output at P_U102 pin 1. Three capacitors already share local copper with those loads. The six joins bring nine more pads onto the regulator output. KiCad connectivity now places 56 of the 230 pads assigned to PWR_V2V5_AUX on that output.

The traces are 4.68 to 25.76 mm long. They terminate at existing supply vias or track endpoints. The adjacent ground plane covers each trace up to the via clearance, and the ground copper around those clearances remains continuous. A fresh refill preserves every plane area. The 2.5 V rail still needs its other branches, a complete load budget and loaded voltage-drop and thermal measurements.

There are 1,531 open power-board connections. Geometry and schematic parity checks pass. ERC retains two isolated-reference warnings. The paired placements match the assembly capture, and via drills clear the plotted mask and paste openings.

[Route endpoints](routes.json) · [Connectivity](connectivity.json) · [Plane check](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
