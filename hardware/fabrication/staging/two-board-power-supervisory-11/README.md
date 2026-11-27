# Rail protection and monitoring traces

Eight surface traces connect comparator inputs, voltage references, feedback and timeout components. Trace lengths range from 3.79 to 14.43 mm and the width is 0.20 mm. The added copper has a continuous adjacent ground reference, clears the enclosure cradle contact regions and uses no vias.

KiCad 10.0.7 confirms eight intended pad-group joins, taking the power board from 1,742 to 1,734 open connections. The footprint positions still match the housing review. The installed assembly, loaded rails and manufacturing constraints require further verification.

[Routes](routes.json) · [Connectivity](connectivity.json) · [Reference-plane coverage](reference-review.json) · [Retained copper](retention.json) · [Placement](placement.json) · [Geometry and schematic parity](drc.json) · [Schematic ERC](erc.json) · [Previous revision](../two-board-power-protection-returns-10/README.md)

The full zone refill preserves all pad groups. All 47 zone-layer copper fields match the independently refilled parent. Saved and refilled layouts both have zero DRC geometry or schematic parity findings. ERC retains two isolated-reference warnings. [Refill comparison](refill-comparison.json)
