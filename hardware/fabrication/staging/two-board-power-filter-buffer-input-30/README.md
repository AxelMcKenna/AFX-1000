# Voltage-reference buffer input

P_U24 pin 3, the noninverting input of the OPA2192, now connects to the relocated 100 nF capacitor P_C242 and its filter-bank branch. The 4.77 mm route uses 0.25 mm traces on F.Cu and B.Cu and one 0.60 mm via with a 0.30 mm drill. The grounded via at P_U24's negative supply pin is 2.35 mm from the signal via and contacts both reference planes.

An independent refill confirms continuous reference copper under both trace segments outside the via clearance. Each of the In1.Cu and In6.Cu ground planes loses 0.7915 mm² at that opening and retains a continuous copper band around it. The measured In4.Cu difference is below 0.000001 mm². The DC input planes retain their previous geometry.

KiCad 10.0.7 confirms the intended pad-group merge and 1,641 remaining open connections. DRC passes geometry and schematic parity. ERC retains two isolated-reference warnings. The paired placement matches the updated assembly capture. The resistor feed and remaining filter-bank branches still need routing and electrical validation.

[Trace and via geometry](routes.json) · [Plane checks](plane-review.json) · [Connectivity](connectivity.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Capacitor placement](../two-board-power-buffer-filter-placement-29/README.md)
