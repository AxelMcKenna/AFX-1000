# Negative 19 V hot-swap controller VIN bias resistor

N_R58 pin 1 reaches N_U18 pin 21 and the existing local VIN capacitor on a 10.90 mm front trace. N_R58 is the 47 kΩ branch between VIN and the negative source. The 0.30 mm trace adds no vias and clears the closest switching-node or pass-gate copper by 3.17 mm in plan view. The series feed through N_R57 and the N_R64 branch still require routing.

KiCad verified the intended pad-group join and 888 remaining open connections.

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
