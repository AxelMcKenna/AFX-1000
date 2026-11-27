# Rail-monitor filter capacitor returns

Twenty-two 100 pF C0G capacitors on rail-monitor sense and reference nodes now connect to analog ground. M_C25 shares an existing ground via through a 1.90 mm trace. The other 21 use 1.15–1.55 mm traces and individual 0.60 mm vias with 0.30 mm drills. All 22 traces are 0.30 mm wide.

The via clearances remove 16.62 mm² from each DC input plane. A 1.485 mm band of continuous copper surrounds each opening on both layers. Native KiCad connectivity confirms the 22 intended joins and 1,612 remaining open connections. Geometry and schematic parity checks pass. ERC retains two isolated-reference warnings. Rail-monitor thresholds still require loaded verification.

[Trace and via geometry](routes.json) · [Plane checks](plane-review.json) · [Connectivity](connectivity.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
