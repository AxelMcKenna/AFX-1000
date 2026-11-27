# Auxiliary supply to the negative-startup bypass group

Three 0.40 mm branches connect E_C25, N_R1 and the N_C3 bypass group to P_U102 pin 1. The N_C3 group includes the VCC pins of N_U32 and N_U10 and nine 100 nF capacitors. All three branches end at existing supply track endpoints. The longest branch is 20.33 mm. The adjacent analog ground plane covers every branch after refill.

The native board and its exported schematic agree on all 230 pads assigned to the auxiliary rail. Of these, 79 connect to the regulator output, including 20 of 81 IC supply pins. 110 connections remain on this rail. Source current, the startup charging transient and installed regulator temperature still require loaded verification.

The power board has 1,521 open connections. Geometry and schematic parity checks pass, with two isolated-reference warnings in ERC. The paired placement matches the assembly capture. Fresh mask and paste plots reproduce the previous via clearances.

[Auxiliary terminal inventory](aux-connectivity.json) · [Route endpoints](routes.json) · [Connectivity](connectivity.json) · [Plane check](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../two-board-via-assembly-review-01/README.md)
