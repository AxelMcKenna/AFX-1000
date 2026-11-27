# Monitor input filters and reference decoupling

M_C38 now bypasses the 5 V input of precision reference M_U6. The two 100 pF C0G capacitors M_C5 and M_C1 now sit by the negative and positive 19 V undervoltage sensing circuits at M_U1. Each capacitor retains its ground connection. Five obsolete ground trace segments at the former positions were removed. The three supply or sense traces are under 1.3 mm long. Powered noise and threshold measurements remain outstanding.

KiCad verified three intended joins and 831 remaining open connections. [Capacitor placement and enclosure clearances](component-placement.json)

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
