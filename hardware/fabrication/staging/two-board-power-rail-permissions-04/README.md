# Rail-disconnect enable inputs

The power board now has 1,886 open connections. Four joins connect existing pad groups on N12_ALLOW, N19_ALLOW and P19_ALLOW. The 27 added segments use 0.20 mm traces on the front and back copper. They add no vias. The longest path is 52.92 mm, from the P19 driver input to its existing resistor group. Enable timing and noise immunity still require electrical qualification.

The full width of the added copper lies over an adjacent connected ground field or existing same-net copper. All 47 saved zone fills and all 5,709 original board objects are preserved. The signal and power board placements match the captured mechanical geometry. KiCad 10.0.7 confirms every intended pad-group merge. The JSON DRC report caps open markers at 499. The native connectivity count covers the whole board.

[Connection paths](routes.json) · [Native connectivity](connectivity.json) · [Geometry and schematic parity](drc.json) · [Ground references](reference-review.json) · [Retained objects](retention.json) · [Paired placement](placement.json) · [Previous revision](../two-board-power-supervisory-03/README.md)
