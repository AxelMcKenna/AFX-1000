# Rail protection and fan ground returns

This revision closes 40 power-board connections in the rail-disconnect, negative-startup and fan circuits. Thirty-seven pads reach ground through dedicated 0.60 mm vias with 0.30 mm drills and 0.30 mm traces. E_C28, E_C61 and E_C65 each use a separate nearby plated ground contact.

KiCad 10.0.7 reports 1,742 opens, down from 1,782. The pad groups match all 40 intended joins. Saved and independently refilled layouts pass geometry and schematic parity checks. The refill preserves all pad groups and matches the parent copper fields across 47 zone-layer pairs. ERC retains two isolated-reference warnings. Footprint poses match the existing housing review. Supply routing, bench qualification and manufacturing stackup approval remain open.

[Routes](routes.json) · [Via geometry](return-review.json) · [Existing ground contacts](existing-contact-review.json) · [Connectivity](connectivity.json) · [Native DRC](drc.json) · [ERC](erc.json) · [Copper retention](retention.json) · [Refill comparison](refill-comparison.json) · [Placement](placement.json) · [Previous revision](../two-board-power-logic-ground-09/README.md)
