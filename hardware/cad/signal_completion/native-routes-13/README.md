# Right output coupling capacitor

A_C514 pin 2 connects directly to A_R508 pin 1 over 8.45 mm on M_AC_R. The 0.20 mm trace stays on B.Cu. The adjacent In6.Cu analog-ground pour contacts an existing grounded via and covers the full trace outside the plated capacitor pad clearance. A continuous ground band extends from 0.21 to 0.36 mm beyond the pad.

An independent KiCad 10.0.7 refill confirms the intended pad-group merge and 127 remaining open connections. All other zone fills match the previous revision. DRC reports zero geometry violations. ERC passes, and schematic parity reports the missing A_U201 codec footprint. The paired placements match the assembly capture. Output-stage performance still requires electrical verification.

[Route and ground anchor](reference-review.json) · [Connectivity and board hashes](native-review.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../native-routes-12/README.md)
