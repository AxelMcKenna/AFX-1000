# Auxiliary 2.5 V feed for the negative startup buffer

The auxiliary regulator at P_U102 pin 1 reaches 208 of its 230 assigned pads. A 0.30 mm branch connects N_U39 pin 14 to the existing distribution via at the end of a 0.40 mm supply trace. A nearby ground via joins the two reference layers.

| Branch load | Trace length (mm) | Ground via spacing (mm) |
| --- | ---: | ---: |
| N_U39:14 | 5.79 | 0.93 |

KiCad verified the expected pad groups. The board has 899 open connections. Loaded voltage drop and supply noise still require measurement.

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
