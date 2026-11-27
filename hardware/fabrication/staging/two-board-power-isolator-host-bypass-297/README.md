# Host-side bypass for the negative 19 V isolator

N_C39 now sits beside N_U19 on the front of the board. It connects directly across the host-side supply and ground pins with two 1.23 mm, 0.30 mm wide traces. The previous bottom-layer ground stub was removed. Both supply and return stay on the host side of the isolation boundary.

KiCad verified the supply connection and the existing ground connectivity. The board has 872 open connections. [Capacitor placement and enclosure clearances](component-placement.json)

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
