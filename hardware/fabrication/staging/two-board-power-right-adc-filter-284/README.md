# Right fan temperature ADC filter capacitor

F_C23 sits on the bottom side near controller pin F_U1:12. Its signal pad reaches the existing ADC via in 0.86 mm and its ground pad reaches an existing ground via in 0.96 mm. The ground via contacts the adjacent In1 and In6 ground regions. F_R23 pin 2, F_C23 pin 1 and F_U1 pin 12 now share a single node. F_R23 pin 1 still requires a connection to the sensor header.

KiCad verified the expected pad groups. The board has 891 open connections. The sensor curve and harness still require bench verification. [Capacitor placement](component-placement.json)

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
