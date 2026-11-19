# Local precision-reference decoupling

P_U4 and its capacitors P_C30 and P_C31 sit on the rear with an existing system-ground via at the end of the local return. All three component bodies clear the projected inductor envelopes. Two 0.40 mm copper connections tie the P_C30 input bypass directly to VIN and ground. The output bypass retains its local connections. KiCad verifies two intended pad-group joins and 1,216 remaining opens. The reference input supply and downstream reference distribution still need routing.

[Routes](routes.json) · [Placement and modeled clearances](component-placement.json) · [Connectivity](connectivity.json) · [Copper refill checks](plane-review.json) · [Paired installation](placement.json) · [DRC](drc.json) · [ERC](erc.json)
