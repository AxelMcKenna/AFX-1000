# Digital rail source monitor

The 0.20 mm DIG_SOURCE_OK trace connects E_U18 pin 1 to E_U39 pin 1 across F.Cu, In3.Cu and B.Cu. Its 15.54 mm path uses two signal vias. The refilled board verifies continuous ground under the traces and ground stitching at the layer transitions.

Native KiCad connectivity confirms the intended join and 1,460 remaining open connections. The auxiliary regulator reaches 96 of its 230 assigned pads. Geometry and schematic parity pass. ERC retains the two isolated-reference warnings. Both PCB placements match the assembly capture.

[Route](routes.json) · [Connectivity](connectivity.json) · [Ground plane changes](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
