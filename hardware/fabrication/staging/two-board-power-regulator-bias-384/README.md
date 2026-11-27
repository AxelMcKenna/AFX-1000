# Analog regulator bias resistor placement

P_R241 moved beside P_C240 and P_C241 on the back of the power board. Both ends of the 6.8 kΩ resistor connect to their respective capacitor pads through 8.01 mm of copper in total. Both routes and resistor lands are fully referenced to analog ground on In6.Cu. The closest modeled body is P_C240, with 0.30 mm clearance. [Layout](layout.json) · [Ground coverage](plane-review.json) · [Component placement](component-placement.json)

KiCad verifies two additional connections, leaving 715 opens. Geometry and schematic parity checks pass and the saved copper fills reproduce. The power schematic retains two isolated-reference ERC warnings. Full housing fit and loaded rail behavior still require qualification. [Connectivity](connectivity.json) · [DRC](drc.json) · [ERC](erc.json) · [Paired placement](placement.json) · [Isolation checks](isolation-midlines.json)
