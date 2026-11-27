# Auxiliary feeds for rail disconnect and negative startup

Seven 0.40 mm branches connect ten more pads to regulator P_U102 pin 1. The E_C59 and E_C80 branches also supply E_U20 and E_U37 through their existing local copper. N_C66 shares a branch with N_C76. E_R72, E_R88, E_U7 and N_C79 complete the other branches. All seven routes terminate at existing supply track endpoints and have continuous adjacent analog ground after refill.

The current schematic assigns 230 pads to the 2.5 V auxiliary rail. Native connectivity puts 66 on the regulator output, including 18 of 81 IC supply pins. 113 connections remain on this rail. The terminal inventory identifies every remaining group of pads. Regulator load, distribution voltage drop, startup and thermal behavior still require verification.

The board has 1,524 open connections. Geometry and schematic parity checks pass. ERC retains two isolated-reference warnings. The paired placements match the assembly capture. Fresh mask and paste plots reproduce the previous via clearances.

[Auxiliary terminal inventory](aux-connectivity.json) · [Route endpoints](routes.json) · [Connectivity](connectivity.json) · [Plane check](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
