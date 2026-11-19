# Right ADC bias

The 0.20 mm trace joins A_R131 pin 2 to the existing A_R137 and A_C125 bias network, using two signal vias and one existing and one new ground stitching via. The refilled layout verifies the adjacent ground under the new In3.Cu and B.Cu traces, as well as the bottom-side copper where the route joins the existing track.

KiCad confirms one intended pad-group join and 109 remaining open connections. Geometry DRC and ERC have zero findings. Schematic parity identifies the missing A_U201 codec footprint. Both boards match the assembly placement capture.

[Routing and reference layers](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Plotted via clearances](../../../fabrication/staging/two-board-via-assembly-review-01/README.md)
