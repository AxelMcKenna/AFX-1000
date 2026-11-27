# Auxiliary regulator source branches

Eight surface branches bring ten additional pads onto the 2.5 V auxiliary regulator output at P_U102 pin 1. These include the supply pins of the E_U8 op amp, E_U1 isolated driver and E_U36 logic buffer. E_C29 and E_C79 already share local copper with their respective ICs. The other newly connected pads are P_R401, E_R131, E_R128, E_R77 and E_C21.

Six 0.40 mm branches terminate at existing supply vias. Two 0.35 mm branches connect at existing supply trace endpoints centered on E_C75 pin 1 and E_R115 pin 2. Ground-plane coverage passes over each branch up to the existing via clearance, with continuous copper around those clearances. KiCad verifies all eight intended pad-group joins after refill. Aggregate rail current, source-path voltage drop and thermal performance still require loaded verification.

The layout has 1,537 open connections. Geometry and schematic parity checks pass. ERC retains two isolated-reference warnings. Paired placements match the assembly capture. Fresh mask and paste plots reproduce the previous via clearances.

[Branch endpoints and widths](routes.json) · [Connectivity](connectivity.json) · [Plane comparison](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
