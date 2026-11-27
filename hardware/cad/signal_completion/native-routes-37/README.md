# Stereo ADC bias and left master output

Pins 2 and 3 of A_J403 now reach the left and right ADC bias networks through existing signal vias. The left master output connection joins A_C513 pin 2 to the A_R504 pin 1 network. Each 0.20 mm trace runs on In5.Cu above the shared ground reference on In6.Cu. The route review records each signal endpoint and its ground stitching.

KiCad confirms three intended pad-group joins and 92 remaining open connections. Geometry DRC and ERC have zero findings. Schematic parity identifies the missing A_U201 codec footprint. Both boards match the assembly placement capture.

[Routing and reference layers](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Plotted via clearances](../../../fabrication/staging/two-board-via-assembly-review-01/README.md)
