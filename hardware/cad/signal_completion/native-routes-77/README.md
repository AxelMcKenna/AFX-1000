# Right-channel ADC bias connection

A_C128 pin 1 now connects to the existing NBIAS_R via through a 6.79 mm front-layer trace. A 14.84 mm detour preserves the bias-window monitor connection and clears the bias route. Both tracks are 0.20 mm wide. In1 ground covers their full widths apart from the existing signal via's antipad. The revision adds no vias and preserves the filled copper areas.

KiCad verifies 49 remaining opens. The sole schematic-parity finding is the missing A_U201 codec footprint.

[Route and return geometry](reference-review.json) · [Connectivity](native-review.json) · [Mechanical placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
