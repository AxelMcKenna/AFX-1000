# Left ADC input filter connection

The 0.20 mm trace connects A_R104:1 to A_C104:1 on the positive left ADC input filter. Its routed length is 3.46 mm. The reference review records the signal via and ground stitching at the layer transition.

KiCad confirms the intended pad-group join and 98 remaining open connections. Geometry DRC and ERC have zero findings. Schematic parity identifies the missing A_U201 codec footprint. Both boards match the assembly placement capture.

[Routing and reference layers](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Plotted via clearances](../../../fabrication/staging/two-board-via-assembly-review-01/README.md)
