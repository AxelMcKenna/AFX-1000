# Host-side bypass for the negative 12 V isolator

N_C55 connects the host supply and ground pins of N_U24. The back-layer capacitor connects to pins 8 and 5 through a pair of 0.60 mm vias with 0.30 mm drills. The supply path is 1.38 mm and the return path is 1.22 mm. The original ground stub was removed. Both paths stay on the host side of the isolation boundary.

KiCad verified the two intended pad-group joins. The board has 870 remaining open connections. [Capacitor placement and enclosure clearances](component-placement.json)

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
