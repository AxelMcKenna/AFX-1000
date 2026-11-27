# Local auxiliary supply routing

Twelve branches connect pads on the fan-health and rail-monitor 3.3 V rails and the internal supplies of the negative-rail startup controllers. The 0.40 mm traces range from 3.00 to 9.62 mm. These local connections leave regulator-to-load distribution and loaded rail checks open.

Native KiCad checks confirm exactly 12 intended pad-group joins and 1,565 remaining open connections. The adjacent analog ground plane covers every new trace after refill. All filled copper areas match the previous revision. Geometry and schematic parity checks pass. ERC retains two isolated-reference warnings. The paired assembly placement matches, and the plotted via-to-mask and via-to-paste clearances are unchanged.

[Route endpoints and dimensions](routes.json) · [Connectivity](connectivity.json) · [Plane comparison](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
