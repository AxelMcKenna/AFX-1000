# Analog regulator feedback divider

P_R244 connects to the feedback input of amplifier P_U24 and completes the divider node joining P_R242 and P_R243. The two branches use 46.25 mm of copper. A local In1.Cu analog-ground extension covers the front-layer traces and resistor lands. The divider signal changes layer beside a ground return via. The nearest modeled body is P_U24, with 0.30 mm clearance. [Layout](layout.json) · [Ground coverage](plane-review.json) · [Component placement](component-placement.json)

All four SET pads and all three divider pads are connected. DRIVE and FB each still have two separate pad groups.

KiCad verifies two additional connections, leaving 711 opens. Geometry and schematic parity checks pass and the saved copper fills reproduce. The power schematic retains two isolated-reference ERC warnings. Full housing fit and loaded rail behavior still require qualification. [Connectivity](connectivity.json) · [DRC](drc.json) · [ERC](erc.json) · [Paired placement](placement.json) · [Isolation checks](isolation-midlines.json)
