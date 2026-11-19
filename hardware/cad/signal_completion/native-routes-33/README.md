# Processing input, preamplifier and receive routing

The left processing input connects relay A_K401 pin 4 to A_R401 pin 1. The right preamplifier output connects A_U103 pin 5 to A_R123 pin 1, and the right receive path connects A_U501 pin 5 to A_R518 pin 1. Each 0.20 mm trace has continuous adjacent ground outside the signal-via clearances. The routing review records the coordinates and ground stitching at each transition.

KiCad confirms three intended pad-group joins and 99 remaining open connections. Geometry DRC and ERC have zero findings. Schematic parity identifies the missing A_U201 codec footprint. Both boards match the assembly placement capture.

[Routing and reference layers](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Plotted via clearances](../../../fabrication/staging/two-board-via-assembly-review-01/README.md)
