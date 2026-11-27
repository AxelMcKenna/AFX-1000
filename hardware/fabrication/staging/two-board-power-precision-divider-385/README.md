# Analog regulator precision divider

The 120 Ω precision resistor P_R242 moved to the back of the power board beside P_R243. Its SET pad reaches P_C241 and the regulator SET network. Its divider pad joins P_R243 directly. The two branches use 17.21 mm of copper in total. Both routes and resistor lands are fully referenced to analog ground on In6.Cu. The closest modeled body is P_C250, with 0.40 mm clearance. [Layout](layout.json) · [Ground coverage](plane-review.json) · [Component placement](component-placement.json)

KiCad verifies two additional connections, leaving 713 opens. Geometry and schematic parity checks pass and the saved copper fills reproduce. The power schematic retains two isolated-reference ERC warnings. Full housing fit and loaded rail behavior still require qualification. [Connectivity](connectivity.json) · [DRC](drc.json) · [ERC](erc.json) · [Paired placement](placement.json) · [Isolation checks](isolation-midlines.json)
