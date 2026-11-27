# Rail-monitor divider ground returns

The analog-ground ends of M_R8, M_R16, M_R58, M_R64, M_R69, M_R75 and M_R77 each connect to PWR_AGND through a 1.15–1.35 mm trace and a dedicated via. The traces are 0.30 mm wide. Each via has a 0.60 mm land and a 0.30 mm drill.

Native refill shows seven clearance openings on each DC input plane, removing 5.54 mm² per layer. Each opening retains at least 1.485 mm of continuous surrounding copper. KiCad confirms all seven intended pad-group joins and 1,634 remaining open connections. Geometry and schematic parity checks pass. ERC retains two isolated-reference warnings. Loaded rail operation and monitor thresholds still need verification.

[Trace geometry](routes.json) · [Plane checks](plane-review.json) · [Connectivity](connectivity.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
