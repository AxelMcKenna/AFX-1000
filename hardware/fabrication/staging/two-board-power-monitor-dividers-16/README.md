# Rail monitor and reset dividers

Six surface traces join divider resistors for the rail-disconnect AUX monitor, negative-startup AUX sense, negative-rail and bias monitors, and the fan power-on reset sense input. All use 0.20 mm copper with a continuous adjacent ground reference. They clear the mounting and cradle contact regions. The board retains the footprint positions used in the housing review.

KiCad confirms the six intended merges, reducing the power-board open count from 1,706 to 1,700. The saved and fully refilled layouts pass geometry and schematic parity checks. All 47 zone-layer copper fields match those of the independently refilled parent. The rail thresholds and startup behavior still require bench verification.

[Routes](routes.json) · [Connectivity](connectivity.json) · [Ground-reference coverage](reference-review.json) · [Retained copper](retention.json) · [Refill comparison](refill-comparison.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../two-board-power-logic-straps-15/README.md)
