# Negative 12 V isolator bypass capacitor

N_C40 is the 100 nF capacitor for the floating supply on N_U24. Its two terminals now connect directly to pins 1 and 4 through separate 0.60 mm vias with 0.30 mm drills. The supply path is 1.53 mm and the return path is 1.37 mm. Both stay on the negative-rail side of the isolation boundary. A 29.54 mm, 0.50 mm wide branch reconnects the capacitor return to the existing PWR_N12_SOURCE network through In5 and In3.

KiCad verified the two intended pad-group joins. The board has 873 remaining open connections. [Capacitor placement and enclosure clearances](component-placement.json)

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
