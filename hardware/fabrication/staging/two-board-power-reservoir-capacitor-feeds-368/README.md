# Positive and negative reservoir capacitor feeds

KiCad verified 3 reservoir capacitor connections. The board has 739 remaining opens. Three 0.80 mm back-layer traces connect the RAW_P22 and RAW_N17 capacitor groups. Analog ground on the adjacent layer extends at least 0.30 mm beyond the trace copper. Each trace terminates fully within its capacitor lands. [Per-transition verification](plane-review.json)

The isolation survey found zero package-midline crossings.

| Net | Connected pad groups | Layer | Length (mm) |
| --- | --- | --- | --- |
| /P_power_supply/RAW_P22 | P_C60:1, P_C6:1 | B.Cu | 8.55 |
| /P_power_supply/RAW_N17 | P_C68:1, P_C56:1 | B.Cu | 10.26 |
| /P_power_supply/RAW_N17 | P_C56:1, P_C69:1 | B.Cu | 2.16 |

[Route geometry](layout.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
