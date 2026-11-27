# Auxiliary feed for the N_U2 and N_U29 logic group

The auxiliary regulator at P_U102 pin 1 reaches 207 of its 230 assigned pads. A 0.30 mm back trace reaches the existing 0.40 mm front supply track at a new via. The front track keeps its original endpoints, width, and path. The nearby ground via connects the reference copper on both layers.

| Branch load | Trace length (mm) | Ground via spacing (mm) |
| --- | ---: | ---: |
| N_U2:8 | 1.90 | 1.31 |

KiCad verified the expected pad groups. The board has 900 open connections. Loaded voltage drop and supply noise still require measurement.

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
