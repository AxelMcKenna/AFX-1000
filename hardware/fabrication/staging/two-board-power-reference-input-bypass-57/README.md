# Protection-reference input bypass

E_C25, the 100 nF input bypass capacitor for E_U7, now sits beside E_C26 on the back of the board. Its positive pad was 13.06 mm from the VIN pin in the previous placement. The new 0.35 mm supply trace measures 2.68 mm across both faces. A 1.25 mm trace connects the capacitor to a ground via. Both reference layers connect through that ground via. The previous supply branch and ground stub were removed.

The nearest modeled body is E_C26, with 0.57 mm clearance from the capacitor envelope. The updated paired placement matches the board files. Exact component heights, installed housing fit and reference stability under load remain unverified.

KiCad verifies identical pad groups before and after the bypass reroute, 1,472 remaining power-board connections and zero geometry or schematic-parity findings. ERC retains two isolated-reference warnings. The 2.5 V auxiliary regulator reaches 95 of its 230 assigned pads.

[Placement measurements](component-placement.json) · [Supply and ground paths](capacitor-routing.json) · [Plane comparison](plane-review.json) · [Paired placement](placement.json) · [Connectivity](connectivity.json) · [DRC](drc.json) · [ERC](erc.json) · [Plotted via clearances](../two-board-via-assembly-review-01/README.md)
