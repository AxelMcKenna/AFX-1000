# Right output series capacitor connection

A_C504 pin 1 connects to A_C516 pin 1 on S_SER_R. The 9.38 mm trace is 0.20 mm wide and stays on B.Cu. Two 0.60 mm ground vias with 0.30 mm drills tie its In6.Cu reference pour to In1.Cu. After refill, ground covers the full trace outside the plated-pad clearances, with a continuous band from 0.21 to 0.36 mm beyond each pad.

KiCad 10.0.7 confirms the intended pad-group join and 125 remaining open connections. The previous filled zones retain equivalent copper geometry. Geometry DRC and ERC pass. Schematic parity reports the missing A_U201 codec footprint. Output-stage performance and manufacturing verification remain open.

[Trace, vias and pad clearances](reference-review.json) · [Connectivity and board hashes](native-review.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../native-routes-14/README.md)
