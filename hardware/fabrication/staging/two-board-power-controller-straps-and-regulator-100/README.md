# Negative rail controller straps and LT3045 regulator connections

N_U18 and N_U23 each gain a short connection between EN and PG on their respective negative source net. P_U22 gains copper between its two input pins and between ILIM and ground as assigned in the schematic. KiCad verifies four intended joins and 1,322 remaining open connections. Loaded operating behavior remains to be checked.

| Width (mm) | Joined pad groups | Layer | Length (mm) |
|---|---|---|---:|
| 0.40 | N_U18 pads 26 and 27 | F.Cu | 0.63 |
| 0.40 | N_U23 pads 26 and 27 | F.Cu | 0.64 |
| 0.40 | P_U22 pads 1 and 2 | F.Cu | 0.50 |
| 0.30 | P_U22 pads 5 and 8 | F.Cu | 3.90 |

[Routes](routes.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
