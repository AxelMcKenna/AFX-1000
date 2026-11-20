# Codec 4.5 V supervisor sense connection

A_R212 now sits 5.22 mm from its previous position on the rear face. Its sense pad connects to A_U206 pin 1 through one 0.60/0.30 mm via. Its ground pad connects to an existing ground via. The old ground stub was removed. Native connectivity verifies the new sense connection and preserves every other pad group. A_R211 pin 2 still needs a connection to this sense node. The board has 54 remaining connections and the ES9292QPRO footprint remains pending.

[Resistor placement](component-placement.json) · [Routes and ground reference](reference-review.json) · [Connectivity](native-review.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
