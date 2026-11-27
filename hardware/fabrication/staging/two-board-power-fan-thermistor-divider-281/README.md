# Left fan thermistor divider

F_R20 moved to bottom copper beside the sensor branch. Two 0.30 mm traces connect it to the 3.3 V supply and the input at F_R21. F_J2 pin 1, F_R20 pin 2 and F_R21 pin 1 now form a single node. The supply reaches all 31 assigned pads. A short 0.40 mm trace maintains the supply junction at the former resistor pad. This revision adds no holes.

KiCad verified the expected pad groups. The board has 894 open connections. The sensor curve and harness still require bench verification. [Resistor placement](component-placement.json)

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
