# Positive overvoltage reference divider ground legs

M_R10 now connects to M_R11 and M_R35 to M_R36 on the bottom of the power board. Both divider resistors keep their ground connections through short branches to existing ground vias. Four new 0.30 mm traces serve the two reference dividers. The two original ground vias remain on the ground net. M_R9 and M_R34 still require routing to these reference nodes.

KiCad verified the intended two pad-group joins and 881 remaining open connections. [Resistor placements](component-placement.json)

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
