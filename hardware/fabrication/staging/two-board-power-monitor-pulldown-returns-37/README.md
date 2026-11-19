# Ground returns for monitor and rail-disconnect circuits

Six connections join E_R27, E_R40, P_R243, P_R303, P_R311 and timing capacitor P_C300 to analog ground. The P_R311 trace terminates at the center of P_C300's ground pad. A separate 1.63 mm trace connects that pad to an existing ground via.

All six traces are 0.30 mm wide. E_R27 and P_R243 each use a new 0.60 mm via with a 0.30 mm drill. Only the E_R27 via passes through the DC input planes. Its clearance removes 0.7915 mm² from each plane and leaves a continuous 1.485 mm band of surrounding copper on both layers.

KiCad confirms the six intended pad-group joins after refill, with 1,593 remaining opens. Geometry and schematic parity checks pass. ERC retains two isolated-reference warnings. Timing and rail thresholds still require loaded verification.

[Trace geometry](routes.json) · [Plane checks](plane-review.json) · [Connectivity](connectivity.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
