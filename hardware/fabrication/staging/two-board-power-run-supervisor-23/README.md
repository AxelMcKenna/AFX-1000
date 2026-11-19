# Power-run supervisor input

The 47 kΩ pull-down P_R112 pin 1 connects to the TPS3890 supervisor sense input P_U201 pin 1 on PWR_POWER_RUN. The 7.71 mm route uses 0.20 mm copper on F.Cu and has continuous adjacent ground on In1.Cu. It uses no vias.

KiCad 10.0.7 confirms the intended pad-group merge and 1,677 remaining open connections. DRC reports zero geometry and schematic parity findings. ERC retains the two existing isolated-reference warnings. The paired placements match the assembly capture. Loaded startup and shutdown qualification remain open.

[Route geometry](routes.json) · [Connectivity](connectivity.json) · [Plane changes](plane-review.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../two-board-power-negative-rail-signals-22/README.md)
