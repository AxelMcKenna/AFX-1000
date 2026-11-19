# Left ADC reference divider

A_R108 pin 2 now reaches the A_R109 pin 1 network through a 2.89 mm rear-layer trace. The former distance to the divider via was 21.80 mm. An In6.Cu ground extension tied to an existing ground via provides a continuous reference along the trace. A_C125 is the nearest modeled component body, with 0.40 mm clearance. The A__REF_ADC1 feed to A_R108 pin 1 remains open.

KiCad confirms one intended pad-group join and 89 remaining open connections. Geometry DRC and ERC have zero findings. Schematic parity identifies the missing A_U201 footprint. Both placements match the updated assembly model. Supplier heights and enclosure fit remain unqualified.

[Resistor placement](component-placement.json) · [Assembly capture](capture.json) · [Routing and reference layers](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Plotted via clearances](../../../fabrication/staging/two-board-via-assembly-review-01/README.md)
