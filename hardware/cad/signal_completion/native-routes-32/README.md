# Left send output relay connection

The 0.20 mm trace connects A_K503:4 to A_R512:1 on the left send output. Its routed length is 27.04 mm. The reference review records the signal vias and ground stitching at both transitions.

KiCad confirms the intended pad-group join and 102 remaining open connections. Geometry DRC and ERC have zero findings. Schematic parity identifies the missing A_U201 codec footprint. Both boards match the assembly placement capture.

[Routing and reference layers](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Plotted via clearances](../../../fabrication/staging/two-board-via-assembly-review-01/README.md)
