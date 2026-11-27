# Monitor comparator and amplifier input resistors

M_R11 and M_R36 join the existing positive 19 V and positive 12 V overvoltage-reference input vias on the bottom of the board. M_R104 joins the existing negative 12 V inverting-amplifier feedback input via. Each connection uses 0.30 mm copper with an adjacent In6 ground reference. The other resistor terminals still require connections to their respective networks.

KiCad verified the intended three pad-group joins and 883 remaining open connections. [Resistor placements](component-placement.json)

[Route geometry](layout.json) · [Regulator reach](rail-connectivity.json) · [Connectivity](connectivity.json) · [Ground coverage](plane-review.json) · [Enclosure check](placement.json) · [Isolation survey](isolation-midlines.json) · [DRC](drc.json) · [ERC](erc.json)
