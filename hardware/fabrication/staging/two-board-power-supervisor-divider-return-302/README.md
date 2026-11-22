# Negative 19 V supervisor divider return

N_R63 closes the local bias-sense divider with N_R62 at N_U20. Its sense terminal connects to the existing divider via with 0.84 mm of B.Cu. Its return terminal connects through a new via to the PWR_N19_SOURCE branch shared by N_U20 and N_U21. That two-layer path measures 1.38 mm. Each segment uses 0.30 mm copper. The supervisor trip threshold still requires a powered measurement.

KiCad verified the two intended pad-group joins. The board has 863 remaining open connections. [Resistor placement and enclosure clearances](component-placement.json)

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
