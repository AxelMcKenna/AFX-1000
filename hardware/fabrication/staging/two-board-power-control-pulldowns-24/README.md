# Control pull-down returns

Five pull-down resistors now connect directly to existing analog-ground contacts. Each connection is 0.30 mm wide and stays on the component layer. All five anchors connect to the same ground network as P_C103 pin 2.

| Resistor | Control signal | Layer | Return length |
| --- | --- | --- | ---: |
| E_R13 | N19_ALLOW | B.Cu | 3.01 mm |
| E_R141 | E28_MASTER_ENABLE | F.Cu | 1.85 mm |
| E_R93 | PWR_RUN_AFTER_FAN | B.Cu | 3.06 mm |
| N_R15 | PWR_NF_GLOBAL_MASTER | B.Cu | 2.21 mm |
| P_R112 | PWR_POWER_RUN | F.Cu | 1.79 mm |

KiCad 10.0.7 confirms all five intended pad-group merges and 1,672 remaining open connections. DRC passes geometry and schematic parity. ERC retains two isolated-reference warnings. Loaded supervisor and startup behavior remain open.

[Return geometry and anchors](routes.json) · [Connectivity](connectivity.json) · [Plane changes](plane-review.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../two-board-power-run-supervisor-23/README.md)
