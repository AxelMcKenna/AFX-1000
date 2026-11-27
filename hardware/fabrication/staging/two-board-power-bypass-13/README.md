# Local bypass for the rail-disconnect Schmitt buffers

E_U36, E_U37 and E_U39 each have a short supply trace to a local 100 nF capacitor. Each trace leaves pin 8 along the pad axis before turning toward the capacitor. A 0.25 mm width clears the adjacent pin on the 0.50 mm pitch packages. Each buffer and its capacitor already share the grounded return plane. These three local supply groups still need a feed from regulator output P_U102 pin 1.

| Buffer | Capacitor | Layer | Supply path |
| --- | --- | --- | --- |
| E_U36 | E_C79 | B.Cu | 2.64 mm |
| E_U37 | E_C80 | B.Cu | 3.26 mm |
| E_U39 | E_C82 | F.Cu | 2.95 mm |

KiCad 10.0.7 verifies the three intended joins, reducing the native open count from 1,720 to 1,717. The traces have continuous ground coverage. A full refill preserves all pad groups and all 47 zone-layer copper fields match the refilled parent. The housing comparison confirms both boards retain their reviewed placement. Supply distribution, bench measurements and manufacturing qualification remain open.

[Local bypass and regulator connectivity](bypass-review.json) · [Routes](routes.json) · [Native connectivity](connectivity.json) · [Reference-plane coverage](reference-review.json) · [Copper retention](retention.json) · [Refill comparison](refill-comparison.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../two-board-power-monitor-control-12/README.md)
