# Local 2.5 V supervisor bypass

The 100 nF capacitor P_C402 is on the front beside P_U201. Its 0.20 mm supply trace runs 1.44 mm from VDD pin 4 to the capacitor. A 0.99 mm trace connects the return to an existing system-ground via. This removes the 33.39 mm branch beneath inductor P_L20. KiCad verifies supply connectivity, one additional ground connection and 1,219 remaining opens. P_U201 ground pin 2 still needs a local connection.

[Routes](routes.json) · [Placement and modeled clearances](component-placement.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Paired installation](placement.json) · [DRC](drc.json) · [ERC](erc.json)
