# Protection control signals

KiCad verified 5 intended pad-group joins and 811 remaining open connections. The table lists the endpoint groups and the layers traversed in order. Layer changes use 0.60 mm vias with 0.30 mm drills. [Return-plane coverage and nearby ground vias](plane-review.json) records the checks for each signal.

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| PWR_NF_MASKED_INVERTED_FAULT | N_U46:11, N_U34:3 | F.Cu, In5.Cu, F.Cu | 27.11 |
| PWR_POWER_RUN | P_U201:1, P_J104:2 | F.Cu, In3.Cu | 38.94 |
| /N_negative_startup_protection/N19_OUTPUT_UV_GOOD | N_U15:2, N_R38:2 | F.Cu, In5.Cu, B.Cu | 42.61 |
| /N_negative_startup_protection/N19_SOURCE_UV_GOOD | N_U14:1, N_R37:2 | F.Cu, In5.Cu, B.Cu | 47.27 |
| /N_negative_startup_protection/N19_ARM_CONDITIONED | N_J1:18, N_R18:1 | In2.Cu | 48.68 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
