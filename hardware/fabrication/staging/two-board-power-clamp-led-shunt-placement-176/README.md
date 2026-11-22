# Negative rail clamp LED shunt placement

The 10 kΩ shunt N_R99 connects the LED anode and cathode of the N_U12 optical relay. Both traces and the resistor sit on the input side of the relay. The projected clearance to relay pads 4–6 is 9.95 mm for the new front copper and 9.30 mm for the new In1 ground pour outline. The refill comparison reports any ground-edge growth outside the added reference copper. The modeled assembly clearances are recorded in [component placement](component-placement.json). KiCad verifies 2 pad-group joins and 1,108 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | N_R99:1 to N_U12:1 | F.Cu | 1.09 |
| 0.20 | N_R99:2 to N_U12:2 | F.Cu | 1.09 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
