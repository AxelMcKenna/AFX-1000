# Negative 19 V regulator bypass capacitor

The 100 nF bypass capacitor P_C53 sits beside negative regulator P_U10 on the front face. The output and ground branches are 1.41 mm and 1.12 mm long. KiCad verifies both connections inside the named lands and 1,255 remaining connections. A dedicated 0.60 mm via and a local extension of the In1 ground plane return the capacitor to analog ground. The 22 µF output capacitor and regulator stability still require work.

[Routes](routes.json) · [Placement and modeled clearances](component-placement.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Paired installation](placement.json) · [DRC](drc.json) · [ERC](erc.json)
