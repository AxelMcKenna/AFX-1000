# Negative-rail reset, overvoltage status and auxiliary fault routing

| Net | Connected pins | Length | Layer changes |
| --- | --- | ---: | ---: |
| N19_BIAS_RESET_N | N_U20.6 to N_U21.6 | 4.15 mm | 0 |
| PWR_N19_OV_OK | E_U9.1 to E_U36.3 | 12.95 mm | 2 |
| ABS_AUX_FAULT | N_U58.4 to N_R17.1 | 45.19 mm | 2 |

The reset stays on F.Cu. Both status routes use 0.20 mm traces on F.Cu, In5.Cu and B.Cu, with 0.60 mm vias and 0.30 mm drills. Existing ground vias connect the reference planes at the F.Cu transitions. In5.Cu and B.Cu share the In6.Cu reference. The four antipads remove 3.166 mm² from each of the In1.Cu and In6.Cu ground planes.

After an independent refill, KiCad 10.0.7 confirms the three intended pad-group joins and 1,678 remaining open connections. The traces retain ground coverage outside via clearances. DRC reports zero geometry and schematic parity violations. ERC retains the two isolated-reference warnings. Both placements match the assembly capture. Loaded startup behavior and manufacturing qualification remain open.

[Route geometry](routes.json) · [Ground coverage](plane-review.json) · [Connectivity](connectivity.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../two-board-power-supervisory-signals-21/README.md)
