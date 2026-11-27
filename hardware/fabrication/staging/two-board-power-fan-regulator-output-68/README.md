# Fan regulator output capacitor

F_C2 is the 10 µF output capacitor for the fan-health circuit’s 3.3 V regulator F_U2. The old front-side placement left its supply pad 5.94 mm from the regulator output. On the back of the board the complete 0.40 mm output connection measures 3.01 mm. A 1.44 mm trace connects the capacitor’s ground pad to the nearby ground via. The old ground stub was removed.

The nearest modeled component is E_C70, with 0.97 mm of body clearance. The paired placement capture checks the board files. Installed housing fit and regulator response under load still require physical verification.

KiCad confirms one new pad-group connection and 1,436 remaining opens. Geometry and schematic parity pass. ERC retains two isolated-reference warnings. The 2.5 V auxiliary regulator still reaches 128 of its 230 assigned pads.

[Component placement](component-placement.json) · [Routing](capacitor-routing.json) · [Connectivity](connectivity.json) · [Plane review](plane-review.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Plotted via clearances](../two-board-via-assembly-review-01/README.md)
