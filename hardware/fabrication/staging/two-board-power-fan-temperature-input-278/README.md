# Left fan temperature sensor connection

F_J2 pin 1 now reaches F_R21 pin 1, the series resistor feeding the left temperature ADC input. The connection uses 0.30 mm copper and a local ground via. The divider pull-up at F_R20 pin 2 still requires routing.

| Branch load | Trace length (mm) | Ground via spacing (mm) |
| --- | ---: | ---: |
| F_R21:1 | 10.98 | 0.89 |

KiCad verified the expected pad groups. The board has 897 open connections. Installed sensor and harness performance still require bench verification.

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
