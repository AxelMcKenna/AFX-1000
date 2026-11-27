# Auxiliary supply feeds

Two 0.40 mm branches connect N_R91 and E_C70 to existing regulator-fed vias. Both branches use In5.Cu and B.Cu, sharing the same In6.Cu ground plane across each transition. The connectivity report identifies the new pad groups supplied by the regulator.

The 2.5 V regulator now reaches 162 of 230 assigned pads. KiCad confirms two intended pad-group joins and 1,415 remaining open connections. Geometry and schematic parity pass. ERC retains the two isolated-reference warnings. Both PCB placements match the assembly capture.

[Auxiliary supply connectivity](aux-connectivity.json) · [Route](routes.json) · [Connectivity](connectivity.json) · [Ground plane changes](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
