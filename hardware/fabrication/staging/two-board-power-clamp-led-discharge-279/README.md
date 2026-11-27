# Clamp LED supply discharge branch

N_R97 pin 1 connects to N_C98 pin 1 with a 0.30 mm trace. The resistor and capacitor share the clamp LED supply node. Its connection to the load switch output at N_U57 pin 6 remains open.

| Branch load | Trace length (mm) | Ground via spacing (mm) |
| --- | ---: | ---: |
| N_C98:1 | 14.83 | 0.89 |

KiCad verified the expected pad groups. The board has 896 open connections. The supply discharge time still requires bench verification.

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
