# Negative bias undervoltage input filter

M_C21 now sits beside M_R62 and comparator M_U3. Its sense terminal reaches M_R62 pin 2 through 1.08 mm of bottom-layer copper. Its ground terminal reaches the local ground via through 1.19 mm. The original ground branch at the previous capacitor location was removed.

KiCad verified the intended sense connection and preserved the original capacitor ground group. The board has 849 open connections. [Resistor placement and enclosure clearances](component-placement.json)

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
