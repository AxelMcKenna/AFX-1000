# Analog regulator power-good feedback input

The LT3045 analog regulator's PGFB input (P_U22 pin 6) joins EN/UV (pin 3) on the schematic's PRE6V net. The 5.86 mm front-layer control trace runs over continuous In1 ground. It uses 0.30 mm copper and adds no vias. The closest projected switch-node or pass-gate copper is 13.97 mm away.

KiCad verified the intended pad-group join. The board has 877 open connections.

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
