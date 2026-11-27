# Reference capacitor ground returns

Nine 100 nF capacitors in the P03_REF_FILTER bank and the 1 µF capacitor P_C252 on P03_REF5 now connect to local analog ground. P_C243, P_C244, P_C248, P_C251 and P_C252 use existing ground contacts, with return traces from 1.82 to 2.85 mm. P_C245, P_C246, P_C247, P_C249 and P_C250 use new 0.60 mm ground vias with 0.30 mm drills, 1.15 to 1.35 mm from their ground pads. Each trace is 0.30 mm wide.

An independent KiCad 10.0.7 refill confirms all ten intended ground joins, reference copper under every return trace and plane contact at each new via. All plane geometries match the refilled parent. Geometry and schematic parity pass. ERC retains the two isolated-reference warnings. The board has 1,653 remaining open connections. The filter bank still needs P_C242's ground return, outstanding signal connections and electrical validation.

[Return geometry and anchors](routes.json) · [Connectivity](connectivity.json) · [Plane changes](plane-review.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../two-board-power-reference-filter-26/README.md)
