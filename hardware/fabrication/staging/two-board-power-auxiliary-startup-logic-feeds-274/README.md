# Auxiliary 2.5 V feeds for startup and rail protection logic

The auxiliary regulator at P_U102 pin 1 reaches 203 of its 230 assigned pads. The branches use 0.30 mm copper. Each transition has a local ground via connecting the two reference layers.

| Branch load | Trace length (mm) | Ground via spacing (mm) |
| --- | ---: | ---: |
| N_U43:14 | 2.43 | 0.99 |
| E_U38:8 | 8.37 | 0.92 |

At the E_U38 transition, native refill trimmed 0.0061 mm² or less from a narrow ground tip on each adjacent reference layer. The ground islands stayed continuous and retained copper under every pre-existing surface connection. KiCad verified the expected pad groups. The board has 901 open connections. Loaded voltage drop and supply noise still require measurement.

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
