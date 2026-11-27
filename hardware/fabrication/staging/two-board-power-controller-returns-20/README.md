# Supervisor and watchdog ground returns

M_U7 and M_U8 each have a 1.30 mm ground trace to a dedicated plated via. N_U9's ground pin and exposed pad share a third via. All four traces are 0.30 mm wide on F.Cu, with ground immediately below on In1.Cu. The vias have 0.60 mm lands and 0.30 mm drills.

Only the two supervisor vias cross the DC input pours. Each retains at least 1.485 mm of continuous input copper around its clearance opening on both In2.Cu and In3.Cu. Together the two openings remove 1.583 mm² per layer. All other zone-layer geometries match an independent refill of the previous board.

KiCad 10.0.7 reports 1,683 open connections. The four new connections survive refill. DRC reports zero geometry and schematic parity findings. ERC retains the two isolated-reference warnings. Both board placements match the assembly capture. Supervisor threshold, watchdog operation and full-load power delivery still require verification.

[Ground connections](routes.json) · [DC input copper](plane-review.json) · [Connectivity](connectivity.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../two-board-power-reference-returns-19/README.md)
