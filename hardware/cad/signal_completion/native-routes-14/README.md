# Right ADC reference divider

A_R125 pin 1 connects to A_C120 pin 1 on REF_DIV_R over a 6.35 mm bottom-layer trace. The 0.20 mm trace stays on B.Cu. A local In6.Cu analog-ground pour covers the full trace width and contacts two existing grounded vias, one near each end.

KiCad 10.0.7 verifies the intended pad-group merge and 126 remaining open connections. All earlier zone layers retain equivalent filled copper after an independent refill. DRC passes geometry and ERC passes. Schematic parity reports the missing A_U201 codec footprint. Reference noise and analog performance still require electrical verification.

[Route and ground contacts](reference-review.json) · [Connectivity and board hashes](native-review.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../native-routes-13/README.md)
