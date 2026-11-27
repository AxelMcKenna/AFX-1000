# Negative 19 V isolator bypass capacitor

N_C13 is the 100 nF capacitor for the floating supply on N_U19. Its two terminals now connect directly to pins 1 and 4 through separate 0.60 mm vias with 0.30 mm drills. The supply path is 1.76 mm and the return path is 1.37 mm. Both stay on the negative-rail side of the isolation boundary. The capacitor remains on the back of the board.

KiCad verified the two intended pad-group joins. The board has 875 remaining open connections. [Capacitor placement and enclosure clearances](component-placement.json)

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
