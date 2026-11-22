# Negative 19 V controller input bypass

The LTC4261 VIN supply input on N_U18 pin 21 reaches the nominal 1 µF N_C6 bypass. The capacitor moves to (296.75, 174.50) mm on the rear side. Two 0.30 mm traces totaling 2.81 mm join the front-side controller to the rear capacitor through one 0.60 mm via with a 0.30 mm drill. N_C6 pin 2 returns to the controller's floating VEE net. The LTC4261 datasheet specifies 1 µF from VIN to VEE.

The BOM retains a hold on effective capacitance under bias. KiCad verified the bypass join and all existing pad partitions. The power layout has 961 remaining opens. The plane review records native fill changes and the distance to the nearest existing VEE via.

[Native routes](layout.json) · [Connectivity](connectivity.json) · [Copper checks](plane-review.json) · [Placement](component-placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
