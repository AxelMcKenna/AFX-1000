# Right ADC filter sense connections

The positive input branch connects A_R120 pin 1 to A_R126 pin 1 through 8.46 mm of copper. The negative branch connects A_C119 pin 1 to A_R127 pin 1 through 11.68 mm. Each route reuses an existing through via and adds one 0.60/0.30 mm via. The 0.20 mm tracks on In5.Cu and B.Cu share a continuous ground reference on In6.Cu. KiCad verifies both pad-group joins and 59 remaining open connections. The ES9292QPRO footprint is pending.

[Routes and ground reference](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
