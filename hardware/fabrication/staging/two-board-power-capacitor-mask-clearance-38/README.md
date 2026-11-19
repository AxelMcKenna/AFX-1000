# Ground via clearance at E_C8

The ground via at (68.0, 135.0) mm intersected the solder-mask opening on both sides of the 1,500 µF capacitor E_C8. Moving it to (68.0, 135.6) mm leaves 0.25 mm nominal clearance between the drill edge and the capacitor land. Two 0.60 mm traces connect the via to the center of pin 1, one on each outer layer.

After refill, the via connects to the In1.Cu and In6.Cu analog ground planes. The filled copper areas and all existing pad connections are preserved. The design has 1,593 open connections, zero geometry or schematic parity violations and two isolated-reference ERC warnings. The paired placements match the assembly capture. The plotted masks and paste layers clear all 949 power-board via drills. The minimum nominal mask clearance elsewhere on the board is 0.0621 mm and needs supplier registration review.

[Via geometry](via-review.json) · [Connectivity](connectivity.json) · [Assembly placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Two-board via measurements](../two-board-via-assembly-review-01/README.md)
