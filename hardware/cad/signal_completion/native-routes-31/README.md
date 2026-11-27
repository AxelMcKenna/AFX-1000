# ADC bias and common-mode connections

The 0.20 mm left bias trace connects A_R116 pin 2 to A_R135 pin 2. On the right channel, A_R128 pin 1 connects to A_R129 pin 1 on the common-mode drive, and A_R126 pin 2 connects to A_R127 pin 2 on the common-mode sense network. The recorded segment coordinates identify each transition and its ground stitching connection.

KiCad confirms three intended pad-group joins and 103 remaining open connections. Geometry DRC and ERC have zero findings. Schematic parity identifies the missing A_U201 codec footprint. Both boards match the assembly placement capture.

[Routing and reference layers](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Plotted via clearances](../../../fabrication/staging/two-board-via-assembly-review-01/README.md)
