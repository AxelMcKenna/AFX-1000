# IC enable, configuration and reference pins

Eleven 0.25 mm traces join pins assigned to the same net within eight packages. They connect enable and supply pins at P_U4, M_U6 and P_U22, configuration pins at P_U25, reference inputs at E_U8 and N_U13, and input straps at the two LTC4261 controllers N_U18 and N_U23. Trace lengths range from 0.50 to 5.20 mm. A local pin connection can still belong to a supply group that is waiting for its feed.

Native KiCad checks confirm exactly 11 intended pad-group joins and 1,472 remaining open connections. The adjacent analog ground plane covers every new trace after refill. All filled copper areas match the preceding revision. The E_C26 placement is retained. Geometry and schematic parity checks pass. ERC retains two isolated-reference warnings. The paired assembly placement matches, and the plotted via-to-mask and via-to-paste clearances are unchanged.

[Route endpoints and dimensions](routes.json) · [Connectivity](connectivity.json) · [Plane comparison](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
