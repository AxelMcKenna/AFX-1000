# Fan supply and protection reference routing

Four 0.40 mm branches join local 5 V pads in the fan circuit, including the F_U2 regulator input and its 10 µF capacitor F_C1. Three more branches join the reference sides of six threshold-setting resistors. These connections do not complete either supply network.

Native KiCad checks confirm exactly 7 intended pad-group joins and 1,509 remaining open connections. The adjacent analog ground plane covers every new trace after refill. All filled copper areas match the previous revision. Geometry and schematic parity checks pass. ERC retains two isolated-reference warnings. The paired assembly placement matches, and the plotted via-to-mask and via-to-paste clearances are unchanged.

[Route endpoints and dimensions](routes.json) · [Connectivity](connectivity.json) · [Plane comparison](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
