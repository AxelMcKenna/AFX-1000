# Protection-reference output capacitor

E_C26, the 1 µF output capacitor for E_U7, now sits underneath the voltage reference. Its positive pad was 32.43 mm from the VREF pin in the previous placement. The new 0.35 mm output trace measures 2.54 mm across both faces. A 1.16 mm trace connects the capacitor to a ground via. Both reference layers connect through that ground via. The old ground stub was removed.

The nearest modeled body is E_R127, with 2.84 mm clearance from the capacitor envelope. The updated paired placement matches the board files. Exact component heights, installed housing fit and reference stability under load remain unverified.

KiCad verifies one intended pad-group join, 1,483 remaining power-board connections and zero geometry or schematic-parity findings. ERC retains two isolated-reference warnings. The 2.5 V auxiliary regulator reaches 95 of its 230 assigned pads.

[Placement measurements](component-placement.json) · [Output and ground paths](capacitor-routing.json) · [Plane comparison](plane-review.json) · [Paired placement](placement.json) · [Connectivity](connectivity.json) · [DRC](drc.json) · [ERC](erc.json) · [Plotted via clearances](../two-board-via-assembly-review-01/README.md)
