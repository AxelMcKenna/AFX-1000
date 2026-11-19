# Rail-disconnect status and right fan tachometer

The conditioned analog-source status signal connects E_U38 pin 2 to E_U24 pin 1 over 13.35 mm. The right fan tachometer buffer connects F_R17 pin 1 to F_U3 pin 4 over 19.77 mm. Each route uses 0.20 mm traces and two 0.60 mm vias with 0.30 mm drills. Both inner runs are on In5.Cu.

The traces have continuous adjacent ground outside their via clearances. All four layer changes have grounded vias within 1.45 mm. Ground wraps around each signal-via clearance on In1.Cu and In6.Cu. The four openings remove 3.166 mm² of ground copper per layer. Independent refills preserve every other zone-layer geometry.

KiCad 10.0.7 reports 1,681 open connections. DRC passes geometry and schematic parity checks. ERC retains the two existing isolated-reference warnings. Both placements match the assembly capture. Functional checks of the disconnect logic and fan tachometer remain open.

[Routes and return vias](routes.json) · [Ground-plane checks](plane-review.json) · [Connectivity](connectivity.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../two-board-power-controller-returns-20/README.md)
