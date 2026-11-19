# Right ADC charge-pump filter resistor

A_R132 now sits on the front beside A_C124. A 3.05 mm trace joins their pin 1 pads over continuous In1.Cu ground. Their previous pad separation was 24.59 mm. The nearest modeled component body is A_C605, with 0.87 mm clearance. A_R132 pin 2 still requires its right-channel bias connection.

KiCad confirms one intended pad-group join and 90 remaining open connections. Geometry DRC and ERC have zero findings. Schematic parity identifies the missing A_U201 footprint. Both placements match the updated assembly model. Supplier heights and enclosure fit remain unqualified.

[Resistor placement](component-placement.json) · [Assembly capture](capture.json) · [Routing and reference layers](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Plotted via clearances](../../../fabrication/staging/two-board-via-assembly-review-01/README.md)
