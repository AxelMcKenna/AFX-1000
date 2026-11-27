# Local regulator and eFuse power pads

Three 0.40 mm traces independently connect the LT3080 output leads at P_U7 to its output exposed pad. At P_U11 two 0.25 mm traces connect the input and current-limit pins to the LT3090 input exposed pad. At P_U22 a 0.25 mm trace joins the ground lead to the LT3045 ground exposed pad. Four 0.50 mm traces join paired input or output lands inside the two TPS25948 eFuses E_U13 and E_U32. Main supply feeds, current sharing, temperature rise and loaded performance still require verification.

Native KiCad checks confirm exactly 10 intended pad-group joins and 1,462 remaining open connections. The adjacent analog ground plane covers every new trace after refill. All filled copper areas match the preceding revision. The E_C25 and E_C26 placements match the paired assembly capture. Geometry and schematic parity checks pass. ERC retains two isolated-reference warnings. The paired assembly placement matches, and the plotted via-to-mask and via-to-paste clearances are unchanged.

[Route endpoints and dimensions](routes.json) · [Connectivity](connectivity.json) · [Plane comparison](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
