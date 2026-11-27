# Fan-health logic supply

An 8.24 mm, 0.40 mm wide trace connects the regulator output capacitor F_C2 to pin 5 of F_U4. A ground via 2.14 mm from the supply via connects the front and back reference planes.

The 3.3 V regulator F_U2 now reaches 5 of 31 assigned pads. KiCad confirms one new pad-group connection and 1,417 remaining opens. Geometry and schematic parity pass. ERC retains the two isolated-reference warnings. The assembly placement matches both PCB files.

The separate 2.5 V auxiliary regulator reaches 159 of 230 assigned pads. [Auxiliary supply connectivity](../two-board-power-auxiliary-layer-transitions-72/aux-connectivity.json)

[Fan supply connectivity](fan-connectivity.json) · [Route](routes.json) · [Connectivity](connectivity.json) · [Ground plane changes](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
