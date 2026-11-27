# Left fan temperature ADC input

F_U1 pin 13, F_C22 pin 1 and F_R21 pin 2 share the filtered left temperature node. The controller connection adds 23.81 mm of 0.30 mm copper on F.Cu and In2.Cu. Both layers share a continuous In1 ground region. The closest switching-node or pass-gate copper is 71.57 mm away in plan view.

KiCad verified the expected pad groups. The board has 889 open connections. Sensor calibration and noise still require bench verification.

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
