# Monitor and clamp resistor placement

The previous auxiliary branches to E_U3 and E_U4 crossed their isolation gaps. Both traces have been removed, reopening two connections. M_R82 returns the regulated 5 V overvoltage sense divider to ground beside comparator M_U4. M_R92 returns the digital 5 V undervoltage reference divider to ground beside M_U4. P_C40 connects the positive 12 V regulator set pin to a nearby ground return. The rear-layer auxiliary supply branch passes outside the N_U12 optical relay land envelope. N_R12 shunts pins 1 and 2 of optical relay N_U11 from the rear layer. Its traces and ground patch stay on the LED side of the isolation barrier. The modeled assembly clearances are recorded in [component placement](component-placement.json). KiCad verifies 9 pad-group joins and 1,083 remaining connections.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.20 | M_R82:1 to M_U4:6 | B.Cu, F.Cu | 2.01 |
| 0.20 | M_R82:2 to P_C103:2 | B.Cu | 0.76 |
| 0.20 | M_R92:1 to M_U4:8 | B.Cu, F.Cu | 1.46 |
| 0.20 | M_R92:2 to P_C103:2 | B.Cu | 0.64 |
| 0.20 | N_R12:1 to N_U11:1 | B.Cu | 0.96 |
| 0.20 | N_R12:2 to N_U11:2 | B.Cu | 3.96 |
| 0.20 | P_C40:1 to P_U8:2 | B.Cu, F.Cu | 5.16 |
| 0.20 | P_C40:2 to P_C103:2 | B.Cu | 3.03 |
| 0.40 | N_C68:1 to N_C57:1 | B.Cu | 18.32 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)

Removing the two crossing traces leaves 73 layer intersections across the surveyed packages. Remaining copper requires review. [Whole-board isolation survey](isolation-midlines.json)

[Projected clearances at isolation components](isolation-clearance.json)

The maximum modeled change in inlet-plane sheet resistance was 0.079%. [Mesh calculations](inlet-sheet-comparison.json)
