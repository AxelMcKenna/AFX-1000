# Positive regulator feedforward capacitor

P_C73, the 68 pF feedforward capacitor, moved beside its 240 kΩ feedback resistor P_R44. The front traces connecting the two parts measure 1.00 mm on the feedback side and 6.77 mm on the output side. Neither connection uses a via. The resistor and capacitor still need their connection to the regulator output rail. [Placement](component-placement.json) · [Routing](layout.json) · [Ground coverage](plane-review.json)

KiCad verified both joins, leaving 695 open connections. Geometry and schematic parity checks pass. The paired placements match the enclosure capture and copper clears the surveyed isolation-package midlines. The power schematic retains two isolated-reference ERC warnings. [Connectivity](connectivity.json) · [DRC](drc.json) · [ERC](erc.json) · [Placement](placement.json) · [Isolation survey](isolation-midlines.json)
