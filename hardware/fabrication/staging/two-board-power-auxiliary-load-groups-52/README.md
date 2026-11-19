# Local 2.5 V supply branches

Sixteen 0.40 mm surface branches join auxiliary supply pads in the rail disconnect, negative startup and power supply circuits. The shortest branch is 2.37 mm and the longest is 17.47 mm. KiCad confirms each intended pad-group join and continuous adjacent ground coverage after refill.

The regulator reaches 85 of 230 assigned pads, including 21 of 81 IC supply pins. The rail still has 89 open connections. Loaded current and regulator temperature remain unverified.

KiCad reports 1,493 open connections across the power board, zero geometry or schematic parity findings and two isolated-reference ERC warnings. The paired placement matches the assembly capture. New solder mask and paste plots reproduce the prior measured via clearances.

[Route endpoints](routes.json) · [Auxiliary terminal inventory](aux-connectivity.json) · [Connectivity](connectivity.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
