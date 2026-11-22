# Negative 19 V controller soft-start timing

N_U18 pin 19 reaches the 100 nF C0G soft-start capacitor N_C29 through 7.72 mm of 0.30 mm copper and one 0.60 mm via with a 0.30 mm drill. The capacitor moves from the front side to (304.25, 171.00) mm on the rear side. Pin 2 returns to the controller's floating VEE net. A 1.00 mm wide, 2.55 mm long In2.Cu connection joins the two existing VEE vias across the soft-start trace. Both vias retain a continuous 0.50 mm wide front copper path into their local return regions.

KiCad verified the soft-start and floating-return connections and all existing pad partitions. The power layout has 951 remaining opens. The plane review records native fill changes and the distance to the nearest existing VEE via.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
