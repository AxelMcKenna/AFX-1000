# Mask clearance at master-enable header E_J6

The power board’s closest via drill to a mask opening was 0.0621 mm from the exposed ground land of E_J6 pin 1. Moving the via from (32.00, 145.00) to (32.15, 144.90) mm gives 0.2405 mm nominal drill-to-land clearance at the header. Two 0.60 mm traces connect the header ground to the via on the outer layers. The via contacts both adjacent ground planes.

Fresh Gerber measurements give minimum drill-to-mask clearances of 0.1246 mm on the front and 0.1250 mm on the back across all 949 power-board vias. Supplier registration and tenting capability remain open. All named pad connections and filled copper areas match revision 39 after refill. The board has 1,577 open connections, zero geometry and parity violations, and two isolated-reference ERC warnings.

[Via geometry](via-review.json) · [Connectivity](connectivity.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Mask and paste measurements](../two-board-via-assembly-review-01/README.md) · [Previous rail-control routing](../two-board-power-rail-control-returns-39/README.md)
