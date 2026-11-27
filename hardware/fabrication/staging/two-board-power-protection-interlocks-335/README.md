# Power protection interlocks

KiCad verified 3 intended pad-group joins and 803 remaining open connections. The table lists the endpoint groups and the layers traversed in order. Layer changes use 0.60 mm vias with 0.30 mm drills. [Return-plane coverage and nearby ground vias](plane-review.json) records the checks for each signal.

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_RUN_AFTER_FAN | E_U43:2, F_J4:2 | B.Cu, F.Cu | 8.86 |
| /P_power_supply/AX03_SOURCE_RESET | P_U202:2, P_U201:6 | F.Cu, In3.Cu, F.Cu | 32.44 |
| /N_negative_startup_protection/N12_OUTPUT_UV_GOOD | N_U15:14, N_R54:2 | F.Cu, B.Cu | 41.12 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
