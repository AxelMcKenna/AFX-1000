# Right fan thermistor pull-up

F_R22 sits on front copper near the right sensor header. Its supply pad connects to the 3.3 V rail at F_C24, and its other pad connects to F_J3 pin 1. The supply reaches all 31 assigned pads. The old supply stub was removed. The series resistor F_R23 still requires a connection to the sensor node.

KiCad verified the expected pad groups. The board has 893 open connections. The sensor curve and harness still require bench verification. [Resistor placement](component-placement.json)

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
