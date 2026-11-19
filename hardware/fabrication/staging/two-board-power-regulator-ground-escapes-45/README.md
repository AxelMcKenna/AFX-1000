# Local regulator and capacitor ground returns

Six 0.60 mm traces provide local ground connections for regulator P_U22 and capacitors P_C41, P_C253, P_C53, P_C51 and P_C38. Three 0.35 mm traces ground resistors P_R114, P_R22 and P_R27. Each branch terminates at its own 0.60 mm via with a 0.30 mm drill. The adjacent plane covers every trace, and KiCad confirms copper contact between each via and the ground plane. The only fill difference is on the In2.Cu module-input feed. Its maximum boundary displacement is 1.16 nm, and its polygon and hole counts are unchanged. Regulator thermal performance and loaded rail behavior still require verification.

KiCad confirms 9 intended pad-group joins after refill, leaving 1,545 open connections. Geometry and schematic parity checks pass. ERC retains two isolated-reference warnings. The paired placement matches the assembly capture. All 962 via drills clear the plotted mask and paste openings.

[Routes](routes.json) · [Connectivity](connectivity.json) · [Plane measurements](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
