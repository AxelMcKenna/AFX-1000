# Left ADC filter capacitors

Both terminals of the differential filter capacitor A_C103 now connect to the corresponding shunt capacitors. Pin 1 reaches A_C104 pin 1 in 4.83 mm on A__ADC_LP. Pin 2 reaches A_C105 pin 1 in 2.98 mm on A__ADC_LN. Both traces are 0.20 mm wide, stay on B.Cu and run over the expanded In6.Cu analog-ground pour. KiCad confirms that the filled pour has one contiguous outline and contacts both existing ground anchors. The full width of both traces has adjacent ground copper.

After an independent zone refill, KiCad 10.0.7 confirms both intended pad-group joins and 128 remaining open connections. All other filled zones match the previous revision. DRC reports zero geometry violations and ERC passes. Schematic parity reports the missing A_U201 codec footprint. The paired placements match the assembly capture. Filter performance still requires electrical verification.

[Filter routes and ground anchors](reference-review.json) · [Connectivity and board hashes](native-review.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../native-routes-11/README.md)
