# Negative 22 V converter output bypass

The 100 nF capacitor P_C10 sits at the filtered output of the Ćuk converter. Its rail terminal reaches P_L3 pin 2 through 1.29 mm of 0.30 mm copper. Its return terminal reaches an existing ground via through 1.53 mm of 0.40 mm copper. Both conductors are on the front layer. Output ripple and load-step performance still require hardware verification.

KiCad verified both intended joins and 834 remaining open connections. [Capacitor placement and enclosure clearances](component-placement.json)

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
