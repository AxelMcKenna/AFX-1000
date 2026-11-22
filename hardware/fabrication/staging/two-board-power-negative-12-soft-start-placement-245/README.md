# Negative 12 V controller soft-start timing

N_U23 pin 19 reaches the 100 nF C0G soft-start capacitor N_C53 through 2.64 mm of 0.30 mm copper and one 0.60 mm via with a 0.30 mm drill. The capacitor moves to (202.75, 171.50) mm on the rear side. Pin 2 returns to the controller's floating VEE net.

KiCad verified the soft-start connection and all existing pad partitions. The power layout has 960 remaining opens. The plane review records native fill changes and the distance to the nearest existing VEE via.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
