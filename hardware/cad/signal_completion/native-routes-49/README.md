# Right channel ADC reference feed

The reference capacitor A_C214 supplies the upper arm of the right channel divider at A_R124. The 37.02 mm connection reuses the capacitor's existing via, runs on In5.Cu and reaches the resistor through one additional 0.60 mm via with a 0.30 mm drill. Both routing layers share the In6.Cu ground reference. The pad groups and continuous ground coverage were checked after refilling the board.

KiCad reports 79 remaining open connections. The codec land pattern and measured reference noise are outstanding.

[Routing and ground checks](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
