# Right ADC sense resistor placement

A_R126 now sits next to A_C118 on the right positive ADC input. The original pad centers were 20.78 mm apart. A 2.56 mm bottom-layer trace now joins them. The resistor was rotated 180 degrees on the bottom side. Its nearest modeled body is A_C118, with 0.57 mm clearance. The common-mode sense connection on the other end of A_R126 still needs routing.

After refill, the 0.20 mm trace runs entirely over continuous In6.Cu analog ground. The same copper island contacts grounded vias near both ends. KiCad verifies the intended connection, 122 remaining opens, zero geometry violations and zero ERC findings. Schematic parity still reports the missing A_U201 footprint. The paired placement matches the updated assembly capture.

[Placement change](component-placement.json) · [Paired placement](placement.json) · [Copper and return path](reference-review.json) · [Connectivity](native-review.json) · [DRC](drc.json) · [ERC](erc.json)
