# Local power-monitor and temperature connections

Nine routes join four summing networks, the left temperature-monitor input filter, the left negative-bias inverter network and three trip-reference networks. The traces run between pads on the same side of the board, using 0.20 mm copper and no vias. Their lengths range from 3.22 to 7.50 mm.

KiCad 10.0.7 confirms the nine intended connections, taking the power PCB from 1,879 to 1,870 opens. Both saved-board and refilled-board checks report zero geometry and schematic parity findings. ERC reports zero errors and retains two ground-pin warnings at N_U19 and N_U24, matching the original integrated schematic. [Schematic ERC](erc.json)

All 5,743 original board objects and all 47 saved zone fills are preserved. The exposed span of each new trace lies over connected adjacent ground. Both main boards retain their enclosure placements. Threshold noise and fan-temperature measurement accuracy still require electrical qualification.

The refill comparison checks all 2,608 physical pad groups and all 47 zone/layer pairs. Every refilled polygon matches the independently refilled parent. Three zones have inherited differences between saved and regenerated outlines, each below 0.0000002 mm². The comparison records those areas. [Refill comparison](refill-comparison.json)

To repeat the comparison from the repository root, use the Python interpreter shipped with KiCad 10.0.7.

```sh
python3 hardware/fabrication/verify_power_surface_refill.py \
  hardware/fabrication/staging/two-board-power-local-monitoring-06 \
  hardware/fabrication/staging/two-board-power-local-thresholds-05
```

[Paths and pad pairs](routes.json) · [Connectivity](connectivity.json) · [Saved-board DRC](drc.json) · [Reference coverage](reference-review.json) · [Retained objects](retention.json) · [Paired placement](placement.json) · [Previous revision](../two-board-power-local-thresholds-05/README.md)
