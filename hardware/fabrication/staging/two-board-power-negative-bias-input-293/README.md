# Negative bias monitor input resistor

M_R106 pin 2 joins the existing M_U5 pin 9 feedback via through 4.83 mm of 0.30 mm copper on B.Cu. Both segments have continuous ground coverage on In6.Cu outside the via clearance. M_R106 pin 1 still needs the negative bias sense feed.

KiCad verified the intended pad-group join. The board has 878 remaining open connections. [Resistor placements](component-placement.json)

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
