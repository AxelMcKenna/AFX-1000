# Bypass relay flyback connection

The flyback diode A_D601 pin 1 now connects to the existing coil-driver copper shared by A_Q601 pin 3 and A_K601 pin 8. Two 0.20 mm traces total 5.63 mm and meet at a 0.60 mm via with a 0.30 mm drill. The return path uses the analog ground plane on In1.Cu and a local In6.Cu ground fill tied to an existing ground via.

KiCad confirms the one intended pad-group merge after refill, leaving 116 open connections. Both traces have adjacent ground coverage. Geometry DRC and ERC have zero findings. Schematic parity still reports the missing codec footprint A_U201. The paired placements and board outlines match the assembly capture.

[Route and ground reference](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via clearances](../../../fabrication/staging/two-board-via-assembly-review-01/README.md)
