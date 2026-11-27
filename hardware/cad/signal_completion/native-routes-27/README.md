# Left ADC common-mode drive

A 0.20 mm trace connects the common-mode driver net at A_U104 pin 7 to A_R113 pin 1. It measures 13.13 mm across In3.Cu and B.Cu. The connection uses one existing signal via, one new signal via and one existing and one new ground stitching via. The refilled layout verifies continuous ground beneath both trace layers and around the two signal vias.

KiCad confirms one intended pad-group join and 110 remaining open connections. Geometry DRC and ERC have zero findings. Schematic parity identifies the missing A_U201 codec footprint. Both boards match the assembly placement capture.

[Routing and reference layers](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Plotted via clearances](../../../fabrication/staging/two-board-via-assembly-review-01/README.md)
