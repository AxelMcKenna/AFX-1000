# Rail-disconnect sense connections

Three routes use 0.25 mm traces to connect the digital-output sense divider to E_U18 and both inverting-amplifier outputs of E_U8 to their resistor branches. Each net crosses through one 0.60 mm via with a 0.30 mm drill. Total copper lengths per net range from 3.11 to 4.19 mm. An existing ground via is within 2.5 mm of each transition and contacts the adjacent ground planes on both sides.

The new clearances remove 2.3745 mm² in total from each of the In1.Cu, In4.Cu, In5.Cu and In6.Cu analog ground fills. The fill changes are confined to the three via clearances. Both surface legs retain their ground reference outside the via clearances. KiCad confirms exactly three new pad-group joins and 1,555 remaining open connections. Geometry and schematic parity checks pass. ERC retains two isolated-reference warnings. Fresh mask and paste plots clear all 952 power-board via drills.

[Route endpoints and via locations](routes.json) · [Plane measurements](plane-review.json) · [Connectivity](connectivity.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
