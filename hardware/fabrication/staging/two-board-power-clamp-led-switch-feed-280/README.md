# Clamp LED load switch output

The 0.30 mm branch runs directly from N_U57 pin 6 to a junction on the capacitor and discharge resistor trace. The switch now reaches N_C98 pin 1, N_R97 pin 1 and N_R11 pin 1. N_R4 pin 1 remains open on this net.

| Branch load | Trace length (mm) | Ground via spacing (mm) |
| --- | ---: | ---: |
| N_U57:6 | 5.92 | 1.12 |

KiCad verified the expected pad groups. The board has 895 open connections. The supply discharge time still requires bench verification.

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
