# Ground connections for references, amplifiers and the rail monitor

Six local vias connect the ground or negative supply pins of E_U7, N_U13, P_U21, P_U24, P_U25 and P_U5 to analog ground. These traces are 1.00–1.80 mm long and 0.30 mm wide. Each via uses a 0.60 mm land and 0.30 mm drill. E_U7 pins 1 and 2 also connect directly across 0.95 mm. TI identifies both DBV pins as internally connected device grounds. [REF35 datasheet, table 5-1](https://www.ti.com/lit/ds/symlink/ref35.pdf)

E_U8's ground-referenced input on pin 3 and its negative supply on pin 4 use separate traces to the same nearby ground via. Their lengths are 1.65 and 2.65 mm. The supply trace clears the input pad.

KiCad 10.0.7 confirms nine intended pad-group merges and 1,644 remaining open connections. After an independent refill, all new traces have continuous adjacent ground and each new via makes ground-plane contact. The existing filled plane geometries match the parent. DRC passes geometry and schematic parity. ERC retains the two isolated-reference warnings. Loaded performance and manufacturing verification remain open.

[Pin and via geometry](routes.json) · [Connectivity](connectivity.json) · [Plane changes](plane-review.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../two-board-power-reference-capacitor-returns-27/README.md)
