# Right thermistor header to ADC series resistor

F_J3 pin 1 and the right temperature pull-up reach F_R23 pin 1 through 24.67 mm of 0.30 mm copper. The trace connects the front resistor pad to In5 through one via and enters the sensor header directly. An existing ground via ties both reference planes near the transition. The closest switching-node or pass-gate copper is 68.70 mm away in plan view.

KiCad verified the expected pad groups. The board has 890 open connections. Sensor calibration and noise still require bench verification.

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
