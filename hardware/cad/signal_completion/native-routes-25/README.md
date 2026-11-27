# Left bypass input

The 0.20 mm trace from connector A_J607 pin 1 to the relay net at A_K601 pin 2 measures 16.32 mm on F.Cu and In3.Cu. One new signal via, one new ground stitching via and one shared ground stitching via use 0.30 mm drills in 0.60 mm lands. A local In4.Cu ground fill runs beneath the inner trace. KiCad refill checks cover the trace, the ground around its layer transitions, and the connections to the front reference plane.

KiCad confirms one intended pad-group join and 113 remaining open connections. Geometry DRC and ERC have zero findings. Schematic parity identifies the missing A_U201 codec footprint. The paired placements match the assembly capture.

[Routing and reference layers](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Plotted via clearances](../../../fabrication/staging/two-board-via-assembly-review-01/README.md)
