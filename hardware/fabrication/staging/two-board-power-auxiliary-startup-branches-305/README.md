# Auxiliary 2.5 V startup distribution

The auxiliary regulator at P_U102 pin 1 reaches 216 of its 230 assigned pads. The new 0.30 mm branches connect the loads listed below to the existing regulator distribution. A ground stitching via beside each supply via joins the front and back reference planes.

| Branch load | Trace length (mm) | Ground via spacing (mm) |
| --- | ---: | ---: |
| N_U52:4 | 13.51 | 0.91 |
| P_R246:1 | 15.75 | 0.90 |

KiCad verified the expected pad groups. The board has 857 open connections. Loaded voltage drop and supply noise still require measurement.

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
