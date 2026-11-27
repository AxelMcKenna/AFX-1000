# Auxiliary supply transitions

Five 0.40 mm branches connect pads across the front and back of the board. Each uses a 0.60 mm via with a 0.30 mm drill. An existing ground via within 3 mm of each transition connects both reference layers. KiCad verified the intended pad groups and copper coverage on both sides after refill.

The regulator reaches 91 of 230 assigned pads, including 26 of 81 IC supply pins. The rail still has 84 open connections. Loaded current and regulator temperature remain unverified.

KiCad reports 1,488 open connections across the power board, zero geometry or schematic parity findings and two isolated-reference ERC warnings. The paired placement matches the assembly capture. New solder mask and paste plots reproduce the prior measured via clearances.

[Route endpoints](routes.json) · [Ground return paths](return-paths.json) · [Auxiliary terminal inventory](aux-connectivity.json) · [Connectivity](connectivity.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
