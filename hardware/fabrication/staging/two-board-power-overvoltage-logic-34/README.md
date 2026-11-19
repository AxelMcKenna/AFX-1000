# Rail-disconnect overvoltage logic

A 5.29 mm trace joins pin 8 of E_U12, an SN74LVC08A quad AND gate, to pin 12 on the same package. The OK_ALL_OV signal runs on B.Cu with 0.20 mm copper width and an In6.Cu analog-ground reference. The route uses no vias.

KiCad connectivity confirms the intended pad-group join and 1,601 remaining open connections. Electrical operation of the rail-disconnect circuit still requires loaded verification.

[Trace geometry](routes.json) · [Connectivity](connectivity.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous bypass-capacitor routes](../two-board-power-monitor-bypass-returns-33/README.md)
