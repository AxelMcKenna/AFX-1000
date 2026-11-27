# Right ADC common-mode sense

A_C121 pin 2 connects directly to A_R127 pin 2 on B.Cu. The 3.77 mm trace is 0.20 mm wide and uses no signal vias. The adjacent In6.Cu analog-ground pour ties into the existing ground network. After refill, ground covers the full trace outside the plated capacitor pad clearance. A continuous ground band extends from 0.21 mm to 0.36 mm beyond that pad.

KiCad 10.0.7 confirms the intended pad-group merge, 130 remaining open connections and equivalent filled copper in all previous zones. Geometry DRC and ERC pass. Schematic parity reports the missing A_U201 codec footprint. Analog performance and installed housing fit still require verification.

[Route, reference and ground anchor](reference-review.json) · [Connectivity and board hashes](native-review.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../native-routes-10/README.md)
