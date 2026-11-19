# Left and right ADC negative-bias branches

The 6.91 mm left branch runs from the existing A_C111 pad-1 connection to A_R115 pin 2. The 7.42 mm right branch connects A_R137 pin 2 to A_C125 pin 1. Each trace is 0.20 mm wide on B.Cu. Both use a shared In6.Cu analog-ground pour that makes copper contact with grounded vias near each end. The pour clears the ADC's existing plane exclusions.

KiCad 10.0.7 confirms both intended pad-group joins after refill and 123 remaining open connections. Ground covers the full width of both traces. Six neighboring ground pours refill against the new pour. Comparing each prior field with the combined filled copper gives less than 0.000001 mm² of difference attributable to lost area per field. The other zone layers retain equivalent geometry.

Geometry DRC and ERC pass. Schematic parity reports the missing A_U201 codec footprint. These branches still require the remaining bias distribution and loaded electrical verification.

[Trace and reference geometry](reference-review.json) · [Connectivity and board hashes](native-review.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../native-routes-15/README.md)
