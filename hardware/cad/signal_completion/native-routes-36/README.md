# Right-channel preamplifier and receive connections

The 0.20 mm preamplifier trace connects A_R414 pin 2 to the A_R123 pin 1 network. The right receive trace connects A_U502 pin 5 to the A_R518 pin 1 network. Each branch uses an existing signal via at its far end. The routing review records the segment coordinates, via identities and adjacent ground connections.

KiCad confirms two intended pad-group joins and 95 remaining open connections. Geometry DRC and ERC have zero findings. Schematic parity identifies the missing A_U201 codec footprint. Both boards match the assembly placement capture.

[Routing and reference layers](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Plotted via clearances](../../../fabrication/staging/two-board-via-assembly-review-01/README.md)
