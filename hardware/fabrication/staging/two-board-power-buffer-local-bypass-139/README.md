# Local 2.5 V buffer bypass

The 100 nF capacitor P_C401 sits on the rear beside the power and ground vias of P_U202. Its supply trace runs 1.17 mm from the input supply via. The return runs 4.10 mm to the ground via. Both existing vias already connect on the front to U202 pins 5 and 3. KiCad confirms that all pad groups retain their original connectivity, with 1,216 remaining opens.

[Routes](routes.json) · [Placement and modeled clearances](component-placement.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Paired installation](placement.json) · [DRC](drc.json) · [ERC](erc.json)
