# Left ADC reference filter

The 0.20 mm trace joins shunt capacitor A_C106 pin 1 to divider resistor A_R109 pin 1. It measures 7.23 mm with one inner-layer span and two bottom-side connections. Continuous ground on In4.Cu references the inner trace, and In6.Cu references both bottom-side traces. The two original component placements are preserved.

KiCad confirms one intended pad-group join and 108 remaining open connections. Geometry DRC and ERC have zero findings. Schematic parity identifies the missing A_U201 codec footprint. Both boards match the assembly placement capture.

[Routing and reference layers](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Plotted via clearances](../../../fabrication/staging/two-board-via-assembly-review-01/README.md)
