# Left receive and bypass-timer routing

A_R517 pin 1 connects to A_R312 pin 2 over 2.09 mm on the left receive net. A_R617 pin 1 connects to A_R616 pin 2 over 3.10 mm on the bypass timer divider. Each connection uses one 0.20 mm bottom-layer trace, with no signal vias. Each trace has a local In6.Cu analog-ground pour that makes copper contact with an existing grounded anchor.

An independent KiCad 10.0.7 zone refill confirms continuous ground under the full width of each trace, both intended pad-group merges and equivalent filled copper in all pre-existing zones. The board has 131 open connections. Geometry DRC and schematic ERC pass. Schematic parity reports the missing A_U201 codec footprint. Both board placements match the assembly capture.

[Trace and anchor identities](reference-review.json) · [Connectivity and board hashes](native-review.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../native-routes-09/README.md)
