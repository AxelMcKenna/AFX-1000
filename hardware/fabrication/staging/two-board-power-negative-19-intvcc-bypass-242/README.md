# Negative 19 V controller logic-supply bypass

The LTC4261 INTVCC output on N_U18 pin 7 reaches the 100 nF N_C7 bypass. Two 0.30 mm traces totaling 1.66 mm join the front-side controller to the rear capacitor through one 0.60 mm via with a 0.30 mm drill. N_C7 pin 2 returns to the controller's floating VEE net. The LTC4261 datasheet specifies 0.1 µF from INTVCC to VEE.

KiCad verified the bypass join and all existing pad partitions. The power layout has 963 remaining opens. The plane review records native fill changes and the distance to the nearest existing VEE via.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
