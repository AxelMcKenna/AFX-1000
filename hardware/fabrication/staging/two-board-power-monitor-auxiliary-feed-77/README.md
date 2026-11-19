# Auxiliary supply feeds

A 0.40 mm branch connects E_C69 pin 1 to an existing regulator-fed via. The In5.Cu and B.Cu segments share the In6.Cu ground plane. The connectivity report identifies the new pad groups supplied by the regulator.

The 2.5 V regulator now reaches 169 of 230 assigned pads. KiCad confirms one intended pad-group join and 1,411 remaining open connections. Geometry and schematic parity pass. ERC retains the two isolated-reference warnings. Both PCB placements match the assembly capture.

[Auxiliary supply connectivity](aux-connectivity.json) · [Route](routes.json) · [Connectivity](connectivity.json) · [Ground plane changes](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
