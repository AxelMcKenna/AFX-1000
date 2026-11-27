# Negative 19 V supervisor bias divider

N_R62 now sits next to N_U20. Its lower end connects to the supervisor sense input with 1.47 mm of copper and one through via. Its upper end joins the local INTVCC supply via with 2.72 mm of 0.30 mm copper on B.Cu. N_R63 still needs its sense and return connections.

KiCad verified the two intended pad-group joins. The board has 865 remaining open connections. [Resistor placement and enclosure clearances](component-placement.json)

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
