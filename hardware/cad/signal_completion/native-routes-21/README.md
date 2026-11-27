# Input bypass relay flyback connection

Two 0.20 mm traces and a 0.60 mm via with a 0.30 mm drill connect the flyback diode A_D603 pin 1 to transistor A_Q603 pin 3 and the existing relay coil connection at A_K602 pin 8. The new copper runs 4.23 mm. The front trace has a ground reference on In1.Cu. The bottom trace has a ground reference on In6.Cu connected to existing ground vias.

KiCad verifies the intended pad-group merge, dropping native opens from 118 to 117. Adjacent ground coverage and via connections pass after a fresh fill. ERC and geometry DRC have zero findings. Schematic parity reports the outstanding A_U201 codec footprint. Both sets of component placements and board outlines match the assembly capture.

[Route and return geometry](reference-review.json) · [Connectivity and source hashes](native-review.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Via manufacturing checks](../../../fabrication/staging/two-board-via-assembly-review-01/README.md)
