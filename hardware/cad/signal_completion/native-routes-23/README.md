# Bypass startup timer

A_U604 pin 4 now connects to A_R618 pin 2. The 0.20 mm timing trace measures 21.51 mm across F.Cu, In3.Cu and B.Cu. Two 0.60 mm vias have 0.30 mm drills. Local analog ground fills on In4.Cu and In6.Cu provide continuous reference copper. The refilled board verifies reference coverage and ground-via contact for all three route layers.

KiCad confirms one intended pad-group join and 115 remaining open connections. Geometry DRC and ERC have zero findings. Schematic parity identifies the missing A_U201 codec footprint. The paired placements match the assembly capture. Startup timing under load remains unverified.

[Routing and reference layers](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Plotted via clearances](../../../fabrication/staging/two-board-via-assembly-review-01/README.md)
