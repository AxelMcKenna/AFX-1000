# Local logic and supervisor input straps

Eight 0.20 mm surface traces join pins that the schematic ties together on the same IC. The routes range from 0.50 to 3.93 mm and use the adjacent ground plane as their reference. The manual-reset route on M_U8 clears the separate sense pin. The native pad groups confirm that it joins only pins 3 and 6.

| Circuit | Connections |
| --- | --- |
| Rail supervisors | Manual reset to VDD on M_U7, M_U8, N_U52 and N_U56 |
| Fan logic | F_U6 direction input to VCCA and F_U8 preset input to VCC |
| Negative-rail logic | Data and preset inputs joined on N_U2 and N_U8 |

The native open count falls from 1,714 to 1,706. Complete supply distribution, loaded startup and manufacturing qualification remain open.

[Pin functions and lengths](pin-functions.json) · [Native connectivity](connectivity.json) · [Routes](routes.json) · [Ground reference coverage](reference-review.json) · [Copper retention](retention.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../two-board-power-aux-supervisor-14/README.md)

KiCad 10.0.7 preserves all connected pad groups after a full refill. All 47 zone-layer copper fields match the independently refilled parent. Saved and refilled boards pass geometry and schematic parity checks. ERC retains two isolated-reference warnings. [Refill comparison](refill-comparison.json)
