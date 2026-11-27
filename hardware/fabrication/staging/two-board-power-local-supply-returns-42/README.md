# Local ground returns for regulators and bypass capacitors

Six 0.60 mm traces connect the exposed pad of fan regulator F_U2 and five capacitor ground pads to existing ground vias. A separate 0.30 mm trace connects F_U2 pin 4 to the same via as its exposed pad. The monitor capacitor returns at M_C50 and M_C51 and the supply capacitor returns at P_C254, P_C37 and P_C60 run 1.59 to 3.22 mm.

Native KiCad checks confirm exactly 7 intended pad-group joins and 1,558 remaining open connections. The adjacent analog ground plane covers every new trace after refill. All filled copper areas match the previous revision. Geometry and schematic parity checks pass. ERC retains two isolated-reference warnings. The paired assembly placement matches, and the plotted via-to-mask and via-to-paste clearances are unchanged.

[Route endpoints and dimensions](routes.json) · [Connectivity](connectivity.json) · [Plane comparison](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
