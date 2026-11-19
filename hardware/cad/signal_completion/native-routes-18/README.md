# Bypass timing and left-channel audio routes

Three connections cross between the front and back layers. The 2.54 mm bypass timer-divider branch connects A_U607 pin 4 to A_R616 pin 2. The 2.96 mm preamplifier branch connects A_U103 pin 3 to A_R107 pin 1. The 10.55 mm output-drive branch connects A_U501 pin 1 to A_R503 pin 1.

Each route uses 0.20 mm traces and one 0.60 mm via with a 0.30 mm drill. On both sides of the board, an independent refill confirms continuous adjacent ground under the trace outside the signal via clearance. Grounded vias near the signal transitions contact both reference layers. The prior copper fields retain their geometry outside the new via openings to within 0.00001 mm² per altered field.

Native KiCad verifies all three pad-group joins and 119 remaining opens. Geometry DRC and ERC pass. Schematic parity reports the missing A_U201 codec footprint. Physical testing of the audio and timing circuits remains open.

[Trace and reference geometry](reference-review.json) · [Connectivity](native-review.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json)
