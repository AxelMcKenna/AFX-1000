# Right fan temperature ADC input

F_R23 pin 2 connects to F_U1 pin 12 through 21.52 mm of 0.30 mm copper on F.Cu and In2.Cu. Both layers share one continuous In1 ground region across the two transitions. The closest switching-node or pass-gate copper is 68.74 mm away in plan view. F_C23 pin 1 and the sensor-side connection to F_R23 pin 1 still require routing.

KiCad verified the expected pad groups. The board has 892 open connections. Sensor calibration and noise still require bench verification.

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
